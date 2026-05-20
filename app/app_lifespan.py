import asyncio
import logging

from sqlalchemy import text

from adapters.database import Base, engine, get_db_session
from adapters.events import subscribe_events
from auth.models import RegisterUserRequest
from entities.marc_sector import MarcRecordIndex, MarcSector  # noqa: F401 — register with ORM
from auth.service import register_user
from config import config
from entities.role import Role
from entities.settings import Settings
from entities.user import User
from settings.models import SETTINGS_MODEL_DISPATCHER
from ws.manager import manager

logger = logging.getLogger(__name__)


async def lifespan(app):
    # Warn about insecure default JWT secret
    if config.auth.secret_key == "your-secret-key":
        logger.warning(
            "AUTH SECRET KEY IS SET TO THE DEFAULT VALUE. "
            "This is insecure — set a strong secret via AUTH_SECRET_KEY env var."
        )

    # Generate database schema
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)

    with get_db_session() as db:
        db.execute(text("""
            CREATE OR REPLACE FUNCTION catalog_records_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := to_tsvector('simple', COALESCE(NEW.search_text, ''));
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
        """))
        db.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'tsvector_update'
                    AND tgrelid = 'catalog_records'::regclass
                ) THEN
                    CREATE TRIGGER tsvector_update
                        BEFORE INSERT OR UPDATE OF search_text
                        ON catalog_records
                        FOR EACH ROW
                        EXECUTE FUNCTION catalog_records_search_vector_update();
                END IF;
            END $$;
        """))
        # Set STORAGE EXTERNAL on marc_sectors.data to skip TOAST compression
        db.execute(text(
            "ALTER TABLE IF EXISTS marc_sectors "
            "ALTER COLUMN data SET STORAGE EXTERNAL"
        ))

        # Enable pg_duckdb extension
        db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_duckdb"))

        # Create analytics materialized view for pg_duckdb faceting
        db.execute(text("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS catalog_records_analytics AS
            SELECT
                cr.id,
                cr.base,
                cr.system_number,
                cr.type_of_record,
                cr.bibliographic_level,
                cr.deleted         AS is_deleted,
                cr.hidden          AS is_hidden,
                (cr.processed_at IS NOT NULL) AS is_processed,

                array_agg(DISTINCT al.linker)
                    FILTER (WHERE al.linker IS NOT NULL)            AS authority_link_linkers,
                array_agg(DISTINCT al.base)
                    FILTER (WHERE al.base IS NOT NULL)              AS authority_link_bases,

                array_agg(DISTINCT cmp.comparator)
                    FILTER (WHERE cmp.comparator IS NOT NULL)       AS comparators,
                array_agg(DISTINCT split_part(cmp.other_record_id, '-', 1))
                    FILTER (WHERE cmp.other_record_id IS NOT NULL)  AS comparison_bases,
                array_agg(DISTINCT CASE
                    WHEN (cmp.result->>'overall_score')::float >= 0.9 THEN 'Excellent'
                    WHEN (cmp.result->>'overall_score')::float >= 0.7 THEN 'Moderate'
                    ELSE 'Poor'
                END)
                    FILTER (WHERE cmp.result->>'overall_score' IS NOT NULL) AS match_qualities,
                array_agg((cmp.result->>'overall_score')::float)
                    FILTER (WHERE cmp.result->>'overall_score' IS NOT NULL) AS overall_scores,

                (SELECT array_agg(DISTINCT expl)
                 FROM comparisons c2,
                      jsonb_array_elements(c2.result->'field_results') fr,
                      jsonb_extract_path_text(fr, 'explanation') expl
                 WHERE c2.main_record_id = cr.id AND expl IS NOT NULL
                ) AS field_explanations,

                array_agg(DISTINCT v.validator)
                    FILTER (WHERE v.validator IS NOT NULL)                  AS validators,
                array_agg(DISTINCT (v.result->>'status'))
                    FILTER (WHERE v.result->>'status' IS NOT NULL)         AS validation_statuses,
                array_agg(DISTINCT (v.result->'target'->>'tag'))
                    FILTER (WHERE v.result->'target'->>'tag' IS NOT NULL)  AS validation_target_tags,

                cr.latest_sync,
                cr.latest_transaction,
                cr.processed_at,
                cr.updated_at
            FROM catalog_records cr
            LEFT JOIN authority_links al ON al.main_record_id = cr.id
            LEFT JOIN comparisons cmp ON cmp.main_record_id = cr.id
            LEFT JOIN validations v ON v.catalog_record_id = cr.id
            GROUP BY cr.id
        """))

        # Unique index enables REFRESH MATERIALIZED VIEW CONCURRENTLY
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_id
            ON catalog_records_analytics (id)
        """))

        db.commit()

    with get_db_session() as db_session:
        # Create default roles
        Role.create_default_roles(db_session)

        # Create admin user if not exists
        admin_user = (
            db_session.query(User)
            .filter(User.email == config.auth.admin.email)
            .first()
        )

        if not admin_user:
            register_user(
                db_session,
                RegisterUserRequest.model_validate(
                    config.auth.admin.model_dump()
                ),
            )

            admin_user = (
                db_session.query(User)
                .filter(User.email == config.auth.admin.email)
                .first()
            )

            admin_role = Role.get_by_name(db_session, "Admin")
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)

            db_session.commit()

        # Create default settings if not exists
        for scope, model_cls in SETTINGS_MODEL_DISPATCHER.items():
            if Settings.get(db_session, scope, model_cls):
                continue

            Settings.save(db_session, scope, model_cls(), model_cls)

    # Start Redis Pub/Sub subscriber for WS event fan-out
    subscriber_task = asyncio.create_task(subscribe_events(manager.broadcast))

    yield

    # Shutdown subscriber
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass


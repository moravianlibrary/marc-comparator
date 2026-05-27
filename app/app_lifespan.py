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
        db.commit()

        # Create analytics denormalized table
        from catalog_records.analytics import init_analytics_table
        init_analytics_table(db)

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


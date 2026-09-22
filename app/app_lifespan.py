import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from adapters.database import get_db_session
from adapters.events import subscribe_events
from auth.models import RegisterUserRequest
from auth.service import register_user
from config import INSECURE_DEFAULT_SECRET_KEY, config
from entities.role import Role
from entities.settings import Settings, SettingsScope
from entities.user import SYSTEM_USER_EMAIL, SYSTEM_USER_ID, User
from settings.models import SETTINGS_MODEL_DISPATCHER
from ws.manager import manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warn about insecure default JWT secret
    if config.auth.secret_key == INSECURE_DEFAULT_SECRET_KEY:
        logger.warning(
            "AUTH SECRET KEY IS SET TO THE DEFAULT VALUE. "
            "This is insecure — set a strong secret via the SECRET_KEY env var."
        )

    # Run database migrations
    from pathlib import Path

    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig

    alembic_ini = Path(__file__).resolve().parent / "alembic.ini"
    alembic_cfg = AlembicConfig(str(alembic_ini))
    await asyncio.to_thread(alembic_command.upgrade, alembic_cfg, "head")

    with get_db_session() as db:
        db.execute(
            text("""
            CREATE OR REPLACE FUNCTION catalog_records_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := to_tsvector('simple', COALESCE(NEW.search_text, ''));
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
        """)
        )
        db.execute(
            text("""
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
        """)
        )
        # Set STORAGE EXTERNAL on marc_sectors.data to skip TOAST compression
        db.execute(
            text("ALTER TABLE IF EXISTS marc_sectors ALTER COLUMN data SET STORAGE EXTERNAL")
        )
        db.commit()

        # Create analytics denormalized table
        from catalog_records.analytics import init_analytics_table

        init_analytics_table(db)

    with get_db_session() as db_session:
        # Create default roles
        Role.create_default_roles(db_session)

        # Create the system user that owns scheduler-created tasks (never logs in)
        system_user = db_session.get(User, SYSTEM_USER_ID)
        if system_user is None:
            system_user = User(
                id=SYSTEM_USER_ID,
                email=SYSTEM_USER_EMAIL,
                first_name="System",
                last_name="Scheduler",
                password_hash="!disabled",
            )
            db_session.add(system_user)
            db_session.commit()

        # The scheduler runs every kind of task on this user's behalf, so it
        # needs every permission. Re-checked on each start so deployments
        # created before this got the role too.
        system_admin_role = Role.get_by_name(db_session, "Admin")
        if system_admin_role not in system_user.roles:
            system_user.roles.append(system_admin_role)
            db_session.commit()

        # Create admin user if not exists
        admin_user = db_session.query(User).filter(User.email == config.auth.admin.email).first()

        if not admin_user:
            register_user(
                db_session,
                RegisterUserRequest.model_validate(config.auth.admin.model_dump()),
            )

            admin_user = (
                db_session.query(User).filter(User.email == config.auth.admin.email).first()
            )
            if admin_user is None:
                raise RuntimeError(
                    f"Admin user '{config.auth.admin.email}' missing right after registration"
                )

            admin_role = Role.get_by_name(db_session, "Admin")
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)

            db_session.commit()

        # Create default settings if not exists
        for scope, model_cls in SETTINGS_MODEL_DISPATCHER.items():
            if Settings.get(db_session, scope, model_cls):
                continue

            Settings.upsert(db_session, scope, model_cls(), model_cls)

        # Reconcile scheduled (redbeat) jobs from persisted settings so
        # default-enabled schedules (e.g. the orphaned-task reaper) exist
        # without waiting for a settings save.
        try:
            from maintenance.models import MaintenanceSettings
            from maintenance.schedule import sync_redbeat_schedule

            maintenance_settings = (
                Settings.get(db_session, SettingsScope.Maintenance, MaintenanceSettings)
                or MaintenanceSettings()
            )
            sync_redbeat_schedule(maintenance_settings)

            from periodic_sync.models import PeriodicSyncSettings
            from periodic_sync.schedule import sync_periodic_sync_schedule

            periodic_sync_settings = (
                Settings.get(db_session, SettingsScope.PeriodicSync, PeriodicSyncSettings)
                or PeriodicSyncSettings()
            )
            sync_periodic_sync_schedule(periodic_sync_settings)

            from harvest.dispatch import reconcile_harvest_schedule

            reconcile_harvest_schedule(db_session)
        except Exception:
            logger.warning("Failed to reconcile redbeat schedule on startup", exc_info=True)

    # Start Redis Pub/Sub subscriber for WS event fan-out
    subscriber_task = asyncio.create_task(subscribe_events(manager.broadcast))

    yield

    # Shutdown subscriber
    # gather(return_exceptions=True) collects the subscriber's CancelledError as a
    # result. Catching CancelledError here would also swallow a cancellation aimed
    # at the lifespan task itself, silently ignoring shutdown.
    subscriber_task.cancel()
    await asyncio.gather(subscriber_task, return_exceptions=True)

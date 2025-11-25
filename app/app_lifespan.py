import asyncio

from esorm import setup_mappings

from adapters.database import Base, engine, get_db_session
from adapters.indexer import (
    is_indexer_available,
    shutdown_indexer,
    startup_indexer,
)
from auth.models import RegisterUserRequest
from auth.service import register_user
from config import config
from entities.role import Role
from entities.settings import Settings
from entities.user import User
from settings.models import SETTINGS_MODEL_DISPATCHER


async def lifespan(app):
    # Generate database schema
    Base.metadata.create_all(bind=engine)

    # Start indexer connection
    await startup_indexer()

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

    # Wait for indexer to be available
    attempt = 1
    while not await is_indexer_available():
        await asyncio.sleep(2**attempt)

        if attempt > 5:
            raise Exception("Indexer is not available")

        attempt += 1

    # Setup ES mappings
    await setup_mappings()

    yield

    # Shutdown indexer connection
    await shutdown_indexer()

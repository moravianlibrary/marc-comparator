import asyncio

from esorm import setup_mappings

from adapters.database import Base, engine, get_db_session
from adapters.indexer import is_indexer_available
from auth.models import RegisterUserRequest
from auth.service import register_user
from config import config
from entities.role import Role
from entities.user import User


async def lifespan(app):
    Base.metadata.create_all(bind=engine)

    with get_db_session() as db_session:
        Role.create_default_roles(db_session)

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

    attempt = 1
    while not await is_indexer_available():
        await asyncio.sleep(2**attempt)

        if attempt > 5:
            raise Exception("Indexer is not available")

        attempt += 1

    await setup_mappings()

    yield

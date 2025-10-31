from adapters.database import Base, engine, get_db_session
from auth.models import RegisterUserRequest
from auth.service import register_user
from config import config
from entities.role import Role
from entities.user import User


def lifespan(app):
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

        admin_user.roles.append(Role.get_by_name(db_session, "Admin"))

    yield

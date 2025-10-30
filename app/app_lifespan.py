from adapters.database import Base, engine, get_db_session
from auth.models import RegisterUserRequest
from auth.service import register_user
from config import config
from entities.user import User


def lifespan(app):
    Base.metadata.create_all(bind=engine)

    with get_db_session() as db_session:
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

    yield

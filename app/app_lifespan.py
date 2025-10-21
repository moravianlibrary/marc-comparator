from adapters.database import Base, engine, get_db_session
from entities.user import User
from config import config
from auth.service import register_user
from auth.models import RegisterUserRequest


def lifespan(app):
    Base.metadata.create_all(bind=engine)

    with get_db_session() as db_session:
        admin_user = db_session.query(User).filter(User.email == config.auth.admin.email).first()

        if not admin_user:
            register_user(db_session, RegisterUserRequest(**config.auth.admin.dict()))

    yield

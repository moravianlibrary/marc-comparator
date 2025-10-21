from contextlib import contextmanager
from typing import TypeVar

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import config

engine = create_engine(config.postgres.url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Session:
    return SessionLocal()


def db_session_generator():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass


DatabaseSession = Session

AnyEntity = TypeVar("AnyEntity", bound=Base)


@contextmanager
def database_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

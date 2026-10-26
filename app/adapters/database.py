from typing import TypeVar

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import config

engine = create_engine(
    config.postgres.url,
    pool_size=config.postgres.pool_size,
    max_overflow=config.postgres.max_overflow,
    pool_timeout=config.postgres.pool_timeout,
    # Recycle and pre-ping protect against silently dropped connections
    # (idle TCP teardown in the cluster, DB restarts): without them an
    # overnight-idle pooled connection surfaces as
    # "SSL SYSCALL error: EOF detected" on first use.
    pool_recycle=config.postgres.pool_recycle,
    pool_pre_ping=True,
    # Pre-ping only checks a connection when it leaves the pool; keepalives
    # keep one alive while it waits on a long statement (analytics rebuild).
    connect_args={
        "keepalives": 1,
        "keepalives_idle": config.postgres.keepalives_idle,
        "keepalives_interval": config.postgres.keepalives_interval,
        "keepalives_count": config.postgres.keepalives_count,
    },
)

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

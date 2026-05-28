import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

import pytest
import pytest_asyncio
from httpx import Response
from marcdantic import MarcRecord
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from adapters.database import Base, DatabaseSession, db_session_generator
from app import app
from config import config

POSTGRES_IMAGE = "postgres:17"
REDIS_IMAGE = "redis:8.0"

FAKE_USER_ID = "12345678-1234-4678-9abc-1234567890ab"

# All table names in dependency order (children first for TRUNCATE CASCADE)
ALL_TABLES = [
    "facet_cube",
    "facet_cube_histogram",
    "catalog_records_analytics",
    "record_reviews",
    "result_snapshots",
    "authority_links",
    "comparisons",
    "validations",
    "catalog_records",
    "marc_record_index",
    "marc_sectors",
    "tasks",
    "settings",
    "user_roles",
    "users",
    "roles",
]

TEST_DATA_DIR = Path(__file__).parent / "integration" / "data"


# --------------------------------------------------------------------------
# Markers
# --------------------------------------------------------------------------
def pytest_configure(config):
    config.addinivalue_line("markers", "db: test requires only Postgres")
    config.addinivalue_line("markers", "redis: test requires Redis")


# --------------------------------------------------------------------------
# Session-scoped containers
# --------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def postgres_container():
    postgres = PostgresContainer(POSTGRES_IMAGE)
    await asyncio.to_thread(postgres.start)
    yield postgres
    await asyncio.to_thread(postgres.stop)


@pytest_asyncio.fixture(scope="session")
async def redis_container():
    redis = RedisContainer(REDIS_IMAGE)
    redis.with_env("maxmemory", "64mb")
    await asyncio.to_thread(redis.start)
    yield redis
    await asyncio.to_thread(redis.stop)


# --------------------------------------------------------------------------
# Session-scoped DB engine (schema created once)
# --------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_container):
    # Import entities so SQLAlchemy registers them
    from entities.authority_link import AuthorityLink  # noqa: F401
    from entities.catalog_record import CatalogRecord  # noqa: F401
    from entities.comparison import Comparison  # noqa: F401
    from entities.marc_sector import MarcRecordIndex, MarcSector  # noqa: F401
    from entities.record_review import RecordReview  # noqa: F401
    from entities.result_snapshot import ResultSnapshot  # noqa: F401
    from entities.validation import Validation  # noqa: F401

    from catalog_records.analytics import init_analytics_table

    engine = create_engine(postgres_container.get_connection_url())
    await asyncio.to_thread(Base.metadata.create_all, engine)

    # Create non-ORM analytics table
    Session = sessionmaker(bind=engine)
    with Session() as session:
        init_analytics_table(session)

    yield engine

    # Drop non-ORM tables before ORM tables
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS facet_cube"))
        conn.execute(text("DROP TABLE IF EXISTS facet_cube_histogram"))
        conn.execute(text("DROP TABLE IF EXISTS catalog_records_analytics"))
        conn.commit()

    await asyncio.to_thread(Base.metadata.drop_all, engine)
    engine.dispose()


# --------------------------------------------------------------------------
# Session-scoped Redis client
# --------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def redis_client(redis_container) -> Redis:
    client = Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(6379),
        db=0,
        decode_responses=True,
    )
    yield client
    client.close()


# --------------------------------------------------------------------------
# Helpers: DB cleanup
# --------------------------------------------------------------------------
def truncate_all_tables(db_session: DatabaseSession):
    """TRUNCATE all tables after a test to get clean state."""
    db_session.rollback()
    for table in ALL_TABLES:
        db_session.execute(
            text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        )
    db_session.commit()


# --------------------------------------------------------------------------
# Helpers: test data loading
# --------------------------------------------------------------------------
def load_test_json(filename: str) -> Dict[str, Any]:
    path = TEST_DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_test_record(filename: str) -> MarcRecord:
    path = TEST_DATA_DIR / filename
    with path.open("rb") as f:
        return MarcRecord.from_mrc(f.read())


def create_catalog_record(
    db_session: DatabaseSession,
    base: str,
    system_number: str,
    marc_record: MarcRecord,
    **kwargs,
):
    """Create a CatalogRecord and store its MARC in sector storage."""
    from adapters.marc_sectors import upsert_record_in_sector
    from entities.catalog_record import CatalogRecord

    record = CatalogRecord(base=base, system_number=system_number, **kwargs)
    record.type_of_record = marc_record.leader_selector.type_of_record
    record.bibliographic_level = marc_record.leader_selector.bibliographic_level
    record.update_search_text_from(marc_record)
    record.save(db_session)

    upsert_record_in_sector(db_session, base, system_number, marc_record._marc)
    db_session.flush()

    return record


# --------------------------------------------------------------------------
# Helpers: response assertions
# --------------------------------------------------------------------------
def assert_response(
    response: Response,
    expected_status: int,
    expected_body: Optional[Dict[str, Any]] = None,
    exclude_field_paths: Set[Tuple[str, ...]] = frozenset(),
):
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, "
        f"got {response.status_code} and body: {response.text}"
    )

    try:
        actual_body = response.json()
    except Exception:
        actual_body = None

    if expected_body is None:
        assert not actual_body, f"Expected no body, but got: {actual_body}"
        return

    assert actual_body is not None, "Expected response body, but got none"

    def filter_excluded(
        d: Dict[str, Any], path: Tuple[str, ...] = ()
    ) -> Dict[str, Any]:
        if not isinstance(d, dict):
            return d
        return {
            k: filter_excluded(v, path + (k,))
            for k, v in d.items()
            if path + (k,) not in exclude_field_paths
        }

    actual_filtered = filter_excluded(actual_body)
    expected_filtered = filter_excluded(expected_body)

    assert (
        actual_filtered == expected_filtered
    ), f"Expected body {expected_filtered}, got {actual_filtered}"

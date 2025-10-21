import asyncio
from typing import Any, AsyncGenerator, Dict, Optional, Set, Tuple

import pytest
import pytest_asyncio
from aleph_nought import AlephClient
from celery import Celery
from esorm import connect, setup_mappings
from httpx import ASGITransport, AsyncClient, Response
from pytest_mock import MockerFixture
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.elasticsearch import ElasticSearchContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.database import Base, DatabaseSession, db_session_generator
from adapters.tasks import TasksClient
from app import app
from auth.models import TokenData
from auth.service import get_current_user
from config import config
from entities.task import Task, TaskType
from entities.user import User

POSTGRES_IMAGE = "postgres:17"
ELASTICSEARCH_IMAGE = "elasticsearch:8.14.0"
REDIS_IMAGE = "redis:8.0"


# ------------------------
# Pytest fixtures
# ------------------------
@pytest_asyncio.fixture(scope="session")
async def postgres_container() -> AsyncGenerator[PostgresContainer, None]:
    """Start a Postgres container for the test session."""
    # Start Postgres container
    postgres = PostgresContainer(POSTGRES_IMAGE)
    await asyncio.to_thread(postgres.start)

    yield postgres

    # Cleanup
    await asyncio.to_thread(postgres.stop)


@pytest_asyncio.fixture(scope="session")
async def elasticsearch_container() -> (
    AsyncGenerator[ElasticSearchContainer, None]
):
    """
    Spin up Elasticsearch in a container
    and yield the container instance.
    """
    # Start Elasticsearch container
    es = ElasticSearchContainer(ELASTICSEARCH_IMAGE)
    es.with_env("ES_JAVA_OPTS", "-Xms256m -Xmx256m")
    es.with_env("xpack.security.enabled", "false")
    await asyncio.to_thread(es.start)

    # Setup mappings
    indexer_session = await connect(
        hosts=es.get_url(),
        basic_auth=("elastic", "changeme"),
        request_timeout=5,
        node_class="httpxasync",
    )
    await setup_mappings(indexer_session)
    await indexer_session.close()

    yield es

    # Cleanup
    await asyncio.to_thread(es.stop)


@pytest_asyncio.fixture(scope="session")
async def redis_container() -> AsyncGenerator[RedisContainer, None]:
    # Start Redis container
    redis = RedisContainer(REDIS_IMAGE)
    redis.with_env("maxmemory", "64mb")
    await asyncio.to_thread(redis.start)

    yield redis

    # Cleanup
    await asyncio.to_thread(redis.stop)


@pytest_asyncio.fixture(scope="class")
async def db_session(
    postgres_container: PostgresContainer, class_mocker: MockerFixture
) -> AsyncGenerator[DatabaseSession, None]:
    """Spin up Postgres in a container and yield a SQLAlchemy session."""
    # SQLAlchemy engine + session
    engine = create_engine(postgres_container.get_connection_url())
    SessionLocal = sessionmaker(bind=engine)
    await asyncio.to_thread(Base.metadata.create_all, engine)

    connection = engine.connect()
    db_session = SessionLocal(bind=connection)

    # Patch dependencies
    app.dependency_overrides[db_session_generator] = lambda: db_session
    class_mocker.patch("adapters.tasks.get_db_session", lambda: db_session)

    yield db_session

    # Cleanup
    db_session.close()
    connection.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest_asyncio.fixture(scope="class")
async def indexer_session(
    elasticsearch_container, class_mocker: MockerFixture
) -> AsyncGenerator[None, None]:
    """
    Yield a function that creates a fresh async indexer session
    inside the test loop.
    """
    class_mocker.patch.object(
        config.elasticsearch, "url", elasticsearch_container.get_url()
    )

    yield


@pytest_asyncio.fixture(scope="class")
async def lock_server_client(
    redis_container: RedisContainer, class_mocker: MockerFixture
) -> AsyncGenerator[Redis, None]:
    """Patch the module's Redis client to use the container Redis."""
    redis_client = Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(6379),
        db=0,
        decode_responses=True,
    )

    class_mocker.patch("adapters.lock_server.lock_server_client", redis_client)


@pytest_asyncio.fixture(scope="class")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


FAKE_USER_ID = "12345678-1234-4678-9abc-1234567890ab"


@pytest.fixture(scope="class")
def user(
    db_session: DatabaseSession, class_mocker: MockerFixture
) -> TokenData:
    db_session.add(
        User(
            id=FAKE_USER_ID,
            first_name="Test",
            last_name="User",
            email="test.user@mzk.cz",
            password_hash="testpasswordhash",
        )
    )
    db_session.commit()

    token_data = TokenData(user_id=FAKE_USER_ID)

    app.dependency_overrides[get_current_user] = lambda: token_data

    return token_data


@pytest.fixture(scope="class")
def tasks_client(
    redis_container: RedisContainer, class_mocker: MockerFixture
) -> TasksClient:
    # Use the test Redis container
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    class_mocker.patch("adapters.tasks.tasks_client", tasks_client)

    return Celery(
        "tasks",
        broker=redis_url,
        result_backend=redis_url,
        broker_connection_retry_on_startup=True,
        timezone=config.timezone,
    )


@pytest.fixture(scope="class")
def aleph_client_registry(class_mocker: MockerFixture) -> AlephClientRegistry:
    fake_client = class_mocker.Mock(spec=AlephClient)
    fake_client_map = {"TEST": fake_client}

    class_mocker.patch.object(
        AlephClientRegistry, "_client_map", fake_client_map
    )

    return AlephClientRegistry


@pytest.fixture(scope="function")
def fake_task(db_session: DatabaseSession, user: TokenData) -> Task:
    task = Task(
        name="Fake task",
        type=TaskType.FetchRecord,
        created_by=user.user_id,
    )
    db_session.add(task)
    db_session.commit()

    return task


def assert_response(
    response: Response,
    expected_status: int,
    expected_body: Optional[Dict[str, Any]] = None,
    exclude_field_paths: Set[Tuple[str, ...]] = frozenset(),
):
    """
    Assert HTTP response status and optionally compare JSON body.

    Args:
        response:
            httpx.Response
        expected_status:
            expected HTTP status code
        expected_body:
            dict of expected JSON keys and values, or None if no body expected
        exclude_field_paths:
            set of key paths to ignore, e.g., {("created_at",), ("user", "id")}
    """
    # Check status code
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, "
        f"got {response.status_code} and body: {response.text}"
    )

    # Parse JSON if possible
    try:
        actual_body = response.json()
    except Exception:
        actual_body = None

    if expected_body is None:
        # No body expected
        assert not actual_body, f"Expected no body, but got: {actual_body}"
        return

    # Body expected
    assert actual_body is not None, "Expected response body, but got none"

    def filter_excluded(
        d: Dict[str, Any], path: Tuple[str, ...] = ()
    ) -> Dict[str, Any]:
        """Recursively remove excluded fields from dict."""
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

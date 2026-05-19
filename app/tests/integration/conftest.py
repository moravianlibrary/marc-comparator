import pytest
import pytest_asyncio
from aleph_nought import AlephClient
from celery import Celery
from elasticsearch import AsyncElasticsearch
from esorm import es
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
from redis import Redis
from sqlalchemy.orm import sessionmaker

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.database import DatabaseSession, db_session_generator
from adapters.tasks import TasksClient
from app import app
from auth.models import TokenData
from auth.service import get_current_user
from config import config
from entities.catalog_record import CatalogRecord
from entities.role import Role
from entities.task import Task, TaskType
from entities.user import User
from tests.conftest import FAKE_USER_ID, truncate_all_tables


# --------------------------------------------------------------------------
# Function-scoped DB session (same pattern as tests/db/)
# --------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine, mocker) -> DatabaseSession:
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    app.dependency_overrides[db_session_generator] = lambda: session
    mocker.patch("adapters.tasks.get_db_session", lambda: session)

    yield session

    session.close()
    cleanup_session = SessionLocal()
    truncate_all_tables(cleanup_session)
    cleanup_session.close()


# --------------------------------------------------------------------------
# Function-scoped ES indexer session (reuses session-scoped es_client)
# --------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def indexer_session(es_client, mocker) -> AsyncElasticsearch:
    # Patch startup/shutdown to no-ops since ES is already connected
    mocker.patch("adapters.indexer.startup_indexer", return_value=True)
    mocker.patch("adapters.indexer.shutdown_indexer")
    return es_client


# --------------------------------------------------------------------------
# Autouse: clean ES documents after each test
# --------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_es_indices(es_client):
    yield
    for index_name in [
        CatalogRecord.__indexer_schema__.ESConfig.index,
        Task.__indexer_schema__.ESConfig.index,
    ]:
        try:
            await es_client.delete_by_query(
                index=index_name,
                body={"query": {"match_all": {}}},
                refresh=True,
                conflicts="proceed",
            )
        except Exception:
            pass


# --------------------------------------------------------------------------
# Function-scoped HTTP client
# --------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        yield c


# --------------------------------------------------------------------------
# Function-scoped user fixture
# --------------------------------------------------------------------------
@pytest.fixture(scope="function")
def user(db_session: DatabaseSession) -> TokenData:
    user = User(
        id=FAKE_USER_ID,
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        password_hash="testpasswordhash",
    )
    user.save(db_session)

    Role.create_default_roles(db_session)
    user.roles.append(Role.get_by_name(db_session, "Admin"))
    db_session.commit()

    token_data = TokenData(user_id=FAKE_USER_ID)
    app.dependency_overrides[get_current_user] = lambda: token_data

    yield token_data

    app.dependency_overrides.pop(get_current_user, None)


# --------------------------------------------------------------------------
# Function-scoped tasks client (Celery pointing to test Redis)
# --------------------------------------------------------------------------
@pytest.fixture(scope="function")
def tasks_client(redis_container, mocker) -> TasksClient:
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    celery_app = Celery(
        "tasks",
        broker=redis_url,
        result_backend=redis_url,
        broker_connection_retry_on_startup=True,
        timezone=config.timezone,
    )

    mocker.patch("adapters.tasks.tasks_client", celery_app)
    return celery_app


# --------------------------------------------------------------------------
# Function-scoped lock server client
# --------------------------------------------------------------------------
@pytest.fixture(scope="function")
def lock_server_client(redis_container, mocker) -> Redis:
    redis_client = Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(6379),
        db=0,
        decode_responses=True,
    )
    mocker.patch("adapters.lock_server.lock_server_client", redis_client)
    return redis_client


# --------------------------------------------------------------------------
# Function-scoped Aleph client registry
# --------------------------------------------------------------------------
@pytest.fixture(scope="function")
def aleph_client_registry(mocker) -> AlephClientRegistry:
    fake_client = mocker.Mock(spec=AlephClient)
    fake_client_map = {"TEST": fake_client}

    mocker.patch.object(AlephClientRegistry, "_client_map", fake_client_map)

    return AlephClientRegistry


# --------------------------------------------------------------------------
# Function-scoped fake task (used by catalog controller tests)
# --------------------------------------------------------------------------
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

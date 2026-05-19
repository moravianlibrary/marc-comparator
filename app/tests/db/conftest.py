import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import sessionmaker

from adapters.database import DatabaseSession, db_session_generator
from app import app
from auth.models import TokenData
from auth.service import get_current_user
from entities.role import Role
from entities.user import User
from tests.conftest import FAKE_USER_ID, truncate_all_tables


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine, mocker) -> DatabaseSession:
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    app.dependency_overrides[db_session_generator] = lambda: session
    mocker.patch("adapters.tasks.get_db_session", lambda: session)

    yield session

    session.close()
    # Clean state for next test
    cleanup_session = SessionLocal()
    truncate_all_tables(cleanup_session)
    cleanup_session.close()


@pytest_asyncio.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        yield c


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

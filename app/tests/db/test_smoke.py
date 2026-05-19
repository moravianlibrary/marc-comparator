import pytest
from httpx import AsyncClient
from sqlalchemy import text

from adapters.database import DatabaseSession
from auth.models import TokenData


@pytest.mark.asyncio
async def test_database_session_smoke(db_session: DatabaseSession):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


@pytest.mark.asyncio
async def test_admin_user_smoke(db_session, user: TokenData):
    assert user is not None
    assert user.user_id == "12345678-1234-4678-9abc-1234567890ab"


@pytest.mark.asyncio
async def test_client_smoke(db_session, client: AsyncClient):
    response = await client.get("/not-found")
    assert response.status_code == 404

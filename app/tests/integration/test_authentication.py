import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from auth.models import RegisterUserRequest
from auth.service import get_password_hash, register_user
from entities.role import Role
from tests.integration.conftest import assert_response


@pytest.fixture(scope="class")
def test_user(db_session: DatabaseSession):
    Role.create_default_roles(db_session)

    register_user(
        db_session,
        RegisterUserRequest(
            email="test.user@example.com",
            first_name="Test",
            last_name="User",
            password="password123",
        ),
    )


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "client",
    "user",
    "test_user",
    "tasks_client",
)
class TestAuthenticationEndpoints:
    @pytest.mark.asyncio
    async def test_user_registration(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/auth/register",
                json={
                    "email": "new.user@example.com",
                    "first_name": "New",
                    "last_name": "User",
                    "password": "password123",
                },
            ),
            201,
        )

    @pytest.mark.asyncio
    async def test_user_registration_existing_email(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/auth/register",
                json={
                    "email": "test.user@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "password": "password123",
                },
            ),
            400,
            {"detail": "User registration failed"},
        )

    @pytest.mark.asyncio
    async def test_user_login(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/auth/token",
                data={
                    "username": "test.user@example.com",
                    "password": "password123",
                },
            ),
            200,
            {
                "access_token": "string",
                "token_type": "bearer",
            },
            {("access_token",)},
        )

    @pytest.mark.asyncio
    async def test_user_login_invalid_username(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/auth/token",
                data={
                    "username": "invalid@example.com",
                    "password": "wrongpassword",
                },
            ),
            401,
            {"detail": "Could not authenticate user"},
        )

    @pytest.mark.asyncio
    async def test_user_login_invalid_password(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/auth/token",
                data={
                    "username": "test.user@example.com",
                    "password": get_password_hash("wrongpassword"),
                },
            ),
            401,
            {"detail": "Could not authenticate user"},
        )

    @pytest.mark.asyncio
    async def test_user_login_invalid_hash(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/auth/token",
                data={
                    "username": "test.user@example.com",
                    "password": "wrongpassword",
                },
            ),
            401,
            {"detail": "Could not authenticate user"},
        )

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient):
        assert_response(
            await client.get("/auth/me"),
            200,
            {
                "id": "12345678-1234-4678-9abc-1234567890ab",
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "User",
                "roles": [
                    {
                        "id": 1,
                        "name": "Admin",
                    },
                ],
            },
        )


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "client",
    "test_user",
    "tasks_client",
)
class TestAuthenticationEndpointsUnauthenticated:
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient):
        response = await client.post(
            "/auth/token",
            data={
                "username": "test.user@example.com",
                "password": "password123",
            },
        )
        token = response.json()["access_token"]

        assert_response(
            await client.get(
                "/auth/me", headers={"Authorization": f"Bearer {token}"}
            ),
            200,
            {
                "id": "some-id",
                "email": "test.user@example.com",
                "first_name": "Test",
                "last_name": "User",
                "roles": [{"id": 2, "name": "Guest"}],
            },
            {("id",)},
        )

    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(self, client: AsyncClient):
        assert_response(
            await client.get("/auth/me"),
            401,
            {"detail": "Not authenticated"},
        )

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        assert_response(
            await client.get(
                "/auth/me", headers={"Authorization": "Bearer invalidtoken"}
            ),
            401,
            {"detail": "Invalid token"},
        )

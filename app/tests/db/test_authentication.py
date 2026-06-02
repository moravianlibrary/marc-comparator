import time
from datetime import UTC

import jwt
import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from auth.models import RegisterUserRequest
from auth.service import (
    create_access_token,
    get_password_hash,
    register_user,
    verify_access_token,
)
from config import config
from entities.role import Role
from tests.conftest import assert_response


@pytest.fixture(scope="function")
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


class TestAuthenticationEndpoints:
    @pytest.mark.asyncio
    async def test_user_registration(self, db_session, user, client: AsyncClient, test_user):
        assert_response(
            await client.post(
                "/auth/sign-up",
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
    async def test_user_registration_existing_email(
        self, db_session, user, client: AsyncClient, test_user
    ):
        assert_response(
            await client.post(
                "/auth/sign-up",
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
    async def test_user_login(self, db_session, user, client: AsyncClient, test_user):
        response = await client.post(
            "/auth/login",
            json={
                "email": "test.user@example.com",
                "password": "password123",
            },
        )
        assert_response(response, 200, {"status": "ok"})
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_user_login_invalid_username(
        self, db_session, user, client: AsyncClient, test_user
    ):
        assert_response(
            await client.post(
                "/auth/login",
                json={
                    "email": "invalid@example.com",
                    "password": "wrongpassword",
                },
            ),
            401,
            {"detail": "Could not authenticate user"},
        )

    @pytest.mark.asyncio
    async def test_user_login_invalid_password(
        self, db_session, user, client: AsyncClient, test_user
    ):
        assert_response(
            await client.post(
                "/auth/login",
                json={
                    "email": "test.user@example.com",
                    "password": get_password_hash("wrongpassword"),
                },
            ),
            401,
            {"detail": "Could not authenticate user"},
        )

    @pytest.mark.asyncio
    async def test_user_login_invalid_hash(self, db_session, user, client: AsyncClient, test_user):
        assert_response(
            await client.post(
                "/auth/login",
                json={
                    "email": "test.user@example.com",
                    "password": "wrongpassword",
                },
            ),
            401,
            {"detail": "Could not authenticate user"},
        )

    @pytest.mark.asyncio
    async def test_get_current_user(self, db_session, user, client: AsyncClient, test_user):
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
                "permissions": [
                    "ReadRecords",
                    "AddRecords",
                    "SyncRecordsFromCatalog",
                    "ReviewRecords",
                    "ManageReviews",
                    "ProcessRecords",
                    "RunPartialRecordTasks",
                    "ManageTasks",
                    "ManageAllTasks",
                    "ManageAccessControl",
                    "ManageAppSettings",
                    "ManageTaskSettings",
                ],
            },
            exclude_field_paths={("permissions",)},
        )


class TestAuthenticationEndpointsUnauthenticated:
    @pytest.mark.asyncio
    async def test_get_current_user(self, db_session, client: AsyncClient, test_user):
        response = await client.post(
            "/auth/login",
            json={
                "email": "test.user@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        client.cookies.set("access_token", response.cookies["access_token"])

        assert_response(
            await client.get("/auth/me"),
            200,
            {
                "id": "some-id",
                "email": "test.user@example.com",
                "first_name": "Test",
                "last_name": "User",
                "roles": [{"id": 2, "name": "Guest"}],
                "permissions": ["ReadRecords"],
            },
            {("id",)},
        )

    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(self, db_session, client: AsyncClient):
        assert_response(
            await client.get("/auth/me"),
            401,
            {"detail": "Not authenticated"},
        )

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session, client: AsyncClient):
        client.cookies.set("access_token", "invalidtoken")
        assert_response(
            await client.get("/auth/me"),
            401,
            {"detail": "Invalid token"},
        )

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, db_session, client: AsyncClient, test_user):
        """A token that has already expired should be rejected."""
        expired_payload = {
            "sub": "test.user@example.com",
            "id": "00000000-0000-0000-0000-000000000000",
            "type": "access",
            "exp": time.time() - 60,  # expired 60s ago
        }
        expired_token = jwt.encode(
            expired_payload,
            config.auth.secret_key,
            algorithm=config.auth.algorithm,
        )
        client.cookies.set("access_token", expired_token)
        assert_response(
            await client.get("/auth/me"),
            401,
            {"detail": "Invalid token"},
        )

    @pytest.mark.asyncio
    async def test_get_current_user_token_missing_id_claim(
        self, db_session, client: AsyncClient, test_user
    ):
        """A token with type='access' but no 'id' claim should raise AuthenticationError."""
        from datetime import datetime, timedelta

        from auth.exceptions import AuthenticationError

        payload = {
            "sub": "test.user@example.com",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        }
        token = jwt.encode(payload, config.auth.secret_key, algorithm=config.auth.algorithm)
        with pytest.raises(AuthenticationError):
            verify_access_token(token)


class TestAuthService:
    def test_verify_token_valid(self, db_session, test_user):
        from datetime import timedelta
        from uuid import uuid4

        uid = uuid4()
        token = create_access_token("test@example.com", uid, timedelta(minutes=5))
        token_data = verify_access_token(token)
        assert token_data.user_id == str(uid)

    def test_verify_token_invalid(self, db_session):
        from auth.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            verify_access_token("not.a.valid.token")

    def test_password_hash_roundtrip(self):
        from auth.service import get_password_hash, verify_password

        password = "testPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrongPassword", hashed)

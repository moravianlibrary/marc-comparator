import pytest
from httpx import AsyncClient

from entities.role import Role


class TestCookieAuth:
    @pytest.mark.asyncio
    async def test_login_sets_cookies(self, db_session, client: AsyncClient):
        Role.create_default_roles(db_session)
        await client.post("/auth/sign-up", json={
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "testpassword123",
        })

        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        assert response.status_code == 200
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_me_with_cookie(self, db_session, user, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_me_without_cookie_returns_401(self, db_session, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_clears_cookies(self, db_session, user, client: AsyncClient):
        response = await client.post("/auth/logout")
        assert response.status_code == 200
        # Cookies should be cleared (max-age=0 / deleted)
        assert response.cookies.get("access_token") is None

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(
        self, db_session, client: AsyncClient
    ):
        Role.create_default_roles(db_session)
        await client.post("/auth/sign-up", json={
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "testpassword123",
        })

        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_issues_new_tokens(self, db_session, client: AsyncClient):
        Role.create_default_roles(db_session)
        await client.post("/auth/sign-up", json={
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "testpassword123",
        })
        login_resp = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        # httpx ASGI transport doesn't enforce cookie path scoping, so we
        # set the refresh_token directly on the client cookie jar.
        refresh_token = login_resp.cookies.get("refresh_token")
        assert refresh_token is not None
        client.cookies.set("refresh_token", refresh_token)
        response = await client.post("/auth/refresh")
        assert response.status_code == 200
        assert "access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_refresh_without_token_returns_401(
        self, db_session, client: AsyncClient
    ):
        response = await client.post("/auth/refresh")
        assert response.status_code == 401


class TestOIDCAuth:
    @pytest.mark.asyncio
    async def test_oidc_login_redirects_when_enabled(
        self, db_session, client: AsyncClient, mocker
    ):
        mocker.patch("config.config.oidc.enabled", True)
        mocker.patch(
            "config.config.oidc.authorization_endpoint",
            "https://keycloak.example.com/auth",
        )
        mocker.patch("config.config.oidc.client_id", "test-client")
        mocker.patch(
            "config.config.oidc.redirect_uri",
            "http://testserver/auth/oidc/callback",
        )

        response = await client.get(
            "/auth/oidc/login?redirect=/tasks",
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert "keycloak.example.com" in response.headers["location"]
        assert "state=%2Ftasks" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_oidc_login_returns_404_when_disabled(
        self, db_session, client: AsyncClient
    ):
        # OIDC is disabled by default
        response = await client.get("/auth/oidc/login")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_oidc_enabled_endpoint(self, db_session, client: AsyncClient):
        response = await client.get("/auth/oidc/enabled")
        assert response.status_code == 200
        assert response.json() == {"enabled": False, "default": False}

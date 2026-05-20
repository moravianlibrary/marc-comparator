import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from adapters.lock_server import one_at_a_time_lock
from app import app
from tests.conftest import FAKE_USER_ID
from ws.controller import router as ws_router

# Lightweight app for WebSocket tests — avoids triggering the full lifespan
_ws_test_app = FastAPI()
_ws_test_app.include_router(ws_router)


class TestWebSocketAuth:
    @pytest.mark.asyncio
    async def test_connect_without_token_rejected(self, db_session):
        with TestClient(_ws_test_app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws"):
                    pass

    @pytest.mark.asyncio
    async def test_connect_with_invalid_token_rejected(self, db_session):
        with TestClient(_ws_test_app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws", cookies={"access_token": "invalid"}):
                    pass

    @pytest.mark.asyncio
    async def test_connect_with_valid_token(self, db_session, user):
        from datetime import timedelta

        from auth.service import create_access_token

        token = create_access_token(
            "admin@example.com", FAKE_USER_ID, timedelta(minutes=5)
        )

        with TestClient(_ws_test_app) as client:
            with client.websocket_connect("/ws", cookies={"access_token": token}) as ws:
                assert ws is not None


class TestGetLocksEndpoint:
    @pytest.mark.asyncio
    async def test_get_locks_empty(
        self, db_session, user, lock_server_client, client
    ):
        response = await client.get("/system/locks")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_locks_with_active_lock(
        self, db_session, user, lock_server_client, client
    ):
        with one_at_a_time_lock("test-visible-lock") as lock:
            assert lock is not None
            response = await client.get("/system/locks")
            assert response.status_code == 200
            assert "test-visible-lock" in response.json()

        # After release, should be gone
        response = await client.get("/system/locks")
        assert response.status_code == 200
        assert "test-visible-lock" not in response.json()

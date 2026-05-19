from unittest.mock import AsyncMock

import pytest

from adapters.events import (
    LockAcquiredEvent,
    LockReleasedEvent,
    TaskProgressEvent,
    TaskStatusEvent,
)
from entities.role import Permission
from ws.manager import Connection, ConnectionManager


def make_connection(user_id: str, permissions: set = None) -> Connection:
    ws = AsyncMock()
    return Connection(
        websocket=ws,
        user_id=user_id,
        permissions=permissions or set(),
    )


class TestConnectionManager:
    def test_connect_and_disconnect(self):
        manager = ConnectionManager()
        conn = make_connection("user-1")

        manager.connect(conn)
        assert len(manager.connections) == 1

        manager.disconnect(conn)
        assert len(manager.connections) == 0

    def test_disconnect_unknown_connection_is_noop(self):
        manager = ConnectionManager()
        conn = make_connection("user-1")
        manager.disconnect(conn)
        assert len(manager.connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_task_status_to_owner(self):
        manager = ConnectionManager()
        owner = make_connection("user-1")
        other = make_connection("user-2")
        manager.connect(owner)
        manager.connect(other)

        event = TaskStatusEvent(
            task_id="t1", status="Success", severity="Info", created_by="user-1"
        )
        await manager.broadcast(event)

        owner.websocket.send_text.assert_called_once()
        other.websocket.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_task_status_to_admin(self):
        manager = ConnectionManager()
        admin = make_connection("user-2", {Permission.ManageAllTasks})
        manager.connect(admin)

        event = TaskStatusEvent(
            task_id="t1", status="Success", severity="Info", created_by="user-1"
        )
        await manager.broadcast(event)

        admin.websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_task_progress_to_owner_only(self):
        manager = ConnectionManager()
        owner = make_connection("user-1")
        other = make_connection("user-2")
        manager.connect(owner)
        manager.connect(other)

        event = TaskProgressEvent(
            task_id="t1", progress=0.5, created_by="user-1"
        )
        await manager.broadcast(event)

        owner.websocket.send_text.assert_called_once()
        other.websocket.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_lock_event_to_all(self):
        manager = ConnectionManager()
        conn1 = make_connection("user-1")
        conn2 = make_connection("user-2")
        manager.connect(conn1)
        manager.connect(conn2)

        event = LockAcquiredEvent(lock_name="catalog_sync_MZK01")
        await manager.broadcast(event)

        conn1.websocket.send_text.assert_called_once()
        conn2.websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_lock_released_to_all(self):
        manager = ConnectionManager()
        conn1 = make_connection("user-1")
        manager.connect(conn1)

        event = LockReleasedEvent(lock_name="recreate-indexes")
        await manager.broadcast(event)

        conn1.websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_dead_connection_removed_on_send_failure(self):
        manager = ConnectionManager()
        dead = make_connection("user-1")
        dead.websocket.send_text.side_effect = Exception("connection closed")
        alive = make_connection("user-2")
        manager.connect(dead)
        manager.connect(alive)

        event = LockAcquiredEvent(lock_name="test")
        await manager.broadcast(event)

        assert dead not in manager.connections
        assert alive in manager.connections

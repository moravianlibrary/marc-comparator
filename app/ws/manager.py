import logging
from dataclasses import dataclass, field

from fastapi import WebSocket

from adapters.events import (
    Event,
    LockAcquiredEvent,
    LockReleasedEvent,
    TaskProgressEvent,
    TaskStatusEvent,
)
from entities.role import Permission

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    websocket: WebSocket
    user_id: str
    permissions: set[Permission] = field(default_factory=set)


class ConnectionManager:
    def __init__(self):
        self.connections: list[Connection] = []

    def connect(self, connection: Connection) -> None:
        self.connections.append(connection)

    def disconnect(self, connection: Connection) -> None:
        try:
            self.connections.remove(connection)
        except ValueError:
            pass

    def _get_recipients(self, event: Event) -> list[Connection]:
        if isinstance(event, (TaskStatusEvent, TaskProgressEvent)):
            return [
                conn
                for conn in self.connections
                if conn.user_id == event.created_by or Permission.ManageAllTasks in conn.permissions
            ]

        if isinstance(event, (LockAcquiredEvent, LockReleasedEvent)):
            return list(self.connections)

        return []

    async def broadcast(self, event: Event) -> None:
        recipients = self._get_recipients(event)
        data = event.model_dump_json()
        dead: list[Connection] = []

        for conn in recipients:
            try:
                await conn.websocket.send_text(data)
            except Exception:
                logger.warning(f"Removing dead WS connection for user {conn.user_id}")
                dead.append(conn)

        for conn in dead:
            self.disconnect(conn)


manager = ConnectionManager()

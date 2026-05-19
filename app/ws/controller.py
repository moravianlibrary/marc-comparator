import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from adapters.database import get_db_session
from auth.service import get_current_user_data, verify_token
from ws.manager import Connection, manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        token_data = verify_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    db_session = get_db_session()
    try:
        user = get_current_user_data(token_data, db_session)
        permissions = set(user.permissions)
    finally:
        db_session.close()

    await websocket.accept()

    connection = Connection(
        websocket=websocket,
        user_id=token_data.user_id,
        permissions=permissions,
    )
    manager.connect(connection)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(connection)

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from adapters.database import get_db_session
from auth.service import get_current_user_data, verify_access_token
from ws.manager import Connection, manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Closing before accepting denies the upgrade, which reaches the browser as
    # an HTTP 403 and a 1006 "abnormal closure" — the 4001 never arrives, so a
    # client that means to stop retrying on auth failure cannot tell one from a
    # dropped network and reconnects forever. Accept first, then close with the
    # code, which is the only way to deliver one.
    async def reject(reason: str) -> None:
        await websocket.accept()
        await websocket.close(code=4001, reason=reason)

    token = websocket.cookies.get("access_token")
    if not token:
        await reject("Missing token")
        return

    try:
        token_data = verify_access_token(token)
    except Exception:
        await reject("Invalid token")
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

from fastapi import APIRouter

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get("/info")
async def get_system_info(
    db_session: DatabaseSessionDep,
    _: CurrentUser,
):
    return await service.get_system_info(db_session)


@router.post(
    "/recreate-indexes",
    dependencies=[WithPermission(Permission.ManageSystem)],
    response_model=TaskSchema,
)
async def recreate_indexes(
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.recreate_indexes(current_user.user_id, db_session)

from fastapi import APIRouter

from adapters.dependencies import (
    DatabaseSessionDep,
    IndexerSessionDep,
    WithPermission,
)
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service

router = APIRouter(
    prefix="/system",
    tags=["System"],
    dependencies=[WithPermission(Permission.ManageSystem)],
)


@router.post("/recreate-indexes", response_model=TaskSchema)
async def validate_records(
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.recreate_indexes(current_user.user_id, db_session)

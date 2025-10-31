from typing import Annotated

from fastapi import APIRouter, Body

from adapters.dependencies import (
    DatabaseSessionDep,
    IndexerSessionDep,
    WithPermission,
)
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .models import ComparisonTaskData

router = APIRouter(
    prefix="/comparison",
    tags=["Comparison"],
    dependencies=[WithPermission(Permission.RunRecordTasks)],
)


@router.post("/task", response_model=TaskSchema)
async def compare_records(
    data: Annotated[ComparisonTaskData, Body(...)],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.compare(data, current_user.user_id, db_session)

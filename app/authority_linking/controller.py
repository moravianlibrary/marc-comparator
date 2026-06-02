from typing import Annotated

from fastapi import APIRouter, Body

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .models import AuthorityLinkingTaskData

router = APIRouter(
    prefix="/authority-linking",
    tags=["Authority Linking"],
    dependencies=[WithPermission(Permission.RunPartialRecordTasks)],
)


@router.post("/task", response_model=TaskSchema)
async def link_records_to_authorities(
    data: Annotated[AuthorityLinkingTaskData, Body(...)],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.authority_linking(data, current_user.user_id, db_session)

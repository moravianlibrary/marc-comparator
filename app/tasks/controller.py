from typing import Annotated

from fastapi import APIRouter, Body, Query

from adapters.dependencies import (
    DatabaseSessionDep,
    IndexerSessionDep,
    WithPermission,
)
from adapters.indexer import IndexerRequest
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .models import TracebackLinesRequestParams

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "/search-own",
    dependencies=[WithPermission(Permission.ManageTasks)],
    response_model=TaskSchema,
)
async def search_own(
    request: Annotated[IndexerRequest, Body()],
    current_user: CurrentUser,
    _: IndexerSessionDep,
):
    return await service.search_own_tasks(request, current_user.user_id)


@router.post(
    "/search-all",
    dependencies=[WithPermission(Permission.ManageAllTasks)],
    response_model=TaskSchema,
)
async def search_all(
    request: Annotated[IndexerRequest, Body()],
    _: IndexerSessionDep,
):
    return await service.search_all_tasks(request)


@router.post(
    "/{task_id}/traceback",
    dependencies=[WithPermission(Permission.ManageTasks)],
)
async def get_traceback_lines(
    task_id: str,
    params: Annotated[TracebackLinesRequestParams, Query()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return service.get_traceback_lines(
        task_id, params, current_user.user_id, db_session
    )


@router.patch(
    "/{task_id}/revoke",
    dependencies=[WithPermission(Permission.ManageTasks)],
    response_model=TaskSchema,
)
async def revoke_task(
    task_id: str,
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.revoke_task(task_id, current_user.user_id, db_session)


@router.post(
    "/delete",
    dependencies=[WithPermission(Permission.ManageAllTasks)],
    response_model=TaskSchema,
)
async def delete_tasks(
    request: Annotated[IndexerRequest, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.delete_tasks(
        request, current_user.user_id, db_session
    )

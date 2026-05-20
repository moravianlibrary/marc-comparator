from typing import Annotated

from fastapi import APIRouter, Body, Query

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .models import SearchTasksRequest, SearchTasksResponse, TracebackLinesRequestParams
from .search import search_tasks

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "/search-own",
    dependencies=[WithPermission(Permission.ManageTasks)],
    response_model=SearchTasksResponse,
)
async def search_own(
    request: Annotated[SearchTasksRequest, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    request.filters.created_by = current_user.user_id
    return search_tasks(request, db_session)


@router.post(
    "/search-all",
    dependencies=[WithPermission(Permission.ManageAllTasks)],
    response_model=SearchTasksResponse,
)
async def search_all(
    request: Annotated[SearchTasksRequest, Body()],
    db_session: DatabaseSessionDep,
):
    return search_tasks(request, db_session)


@router.get(
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
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.delete_tasks(
        current_user.user_id, db_session
    )

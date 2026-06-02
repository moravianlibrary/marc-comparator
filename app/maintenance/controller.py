from fastapi import APIRouter

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema
from tasks import service as tasks_service

from . import service

router = APIRouter(
    prefix="/maintenance",
    tags=["Maintenance"],
    dependencies=[WithPermission(Permission.ManageAppSettings)],
)


@router.post("/refresh-analytics", response_model=TaskSchema)
async def refresh_analytics(
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.refresh_analytics(current_user.user_id, db_session)


@router.post("/cleanup-stale-locks", response_model=TaskSchema)
async def cleanup_stale_locks(
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.cleanup_stale_locks(current_user.user_id, db_session)


@router.post("/compact-sectors", response_model=TaskSchema)
async def compact_sectors(
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.compact_sectors(current_user.user_id, db_session)


@router.post("/rebuild-search-vectors", response_model=TaskSchema)
async def rebuild_search_vectors(
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.rebuild_search_vectors(current_user.user_id, db_session)


@router.post("/delete-tasks", response_model=TaskSchema)
async def delete_tasks(
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    max_age_days: int | None = None,
):
    return await tasks_service.delete_tasks(current_user.user_id, db_session, max_age_days)

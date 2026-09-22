from typing import Annotated

from fastapi import APIRouter, Body

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .models import HarvestPluginStatus, HarvestRunRequest

router = APIRouter(
    prefix="/harvest",
    tags=["Plugin Harvest"],
    dependencies=[WithPermission(Permission.ManageAppSettings)],
)


@router.get("/plugins", response_model=list[HarvestPluginStatus])
def get_plugins(db_session: DatabaseSessionDep):
    return service.list_plugins(db_session)


@router.post("/plugins/{plugin_name}/run", response_model=TaskSchema)
async def run_plugin(
    plugin_name: str,
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    request: Annotated[HarvestRunRequest, Body()],
):
    return await service.enqueue_harvest(
        plugin_name,
        str(current_user.user_id),
        db_session,
        full_rebuild=request.full_rebuild,
    )

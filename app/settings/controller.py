from typing import Annotated

from fastapi import APIRouter, Body, Path

from adapters.dependencies import DatabaseSessionDep, WithPermission
from entities.role import Permission
from entities.settings import RecordToolsSettingsScope, SystemSettingsScope
from settings.models import AppSettingsSchemas, TaskSettingsSchemas

from . import service

router = APIRouter(prefix="/settings")

system_settings_router = APIRouter(
    prefix="/system",
    tags=["System Settings"],
    dependencies=[WithPermission(Permission.ManageAppSettings)],
)
record_tools_settings_router = APIRouter(
    prefix="/record-tools",
    tags=["Record Tools Configs"],
    dependencies=[WithPermission(Permission.ManageTaskSettings)],
)


@system_settings_router.get("/{scope}", response_model=AppSettingsSchemas)
async def get_app_settings(
    scope: Annotated[SystemSettingsScope, Path()],
    db_session: DatabaseSessionDep,
):
    return service.get_settings(scope, db_session)


@system_settings_router.post("/{scope}", response_model=AppSettingsSchemas)
async def set_app_settings(
    scope: Annotated[SystemSettingsScope, Path()],
    settings: Annotated[AppSettingsSchemas, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(scope, settings, db_session)


@record_tools_settings_router.get(
    "/{scope}", response_model=TaskSettingsSchemas
)
async def get_task_settings(
    scope: Annotated[RecordToolsSettingsScope, Path()],
    db_session: DatabaseSessionDep,
):
    return service.get_settings(scope, db_session)


@record_tools_settings_router.post(
    "/{scope}", response_model=TaskSettingsSchemas
)
async def set_task_settings(
    scope: Annotated[RecordToolsSettingsScope, Path()],
    settings: Annotated[TaskSettingsSchemas, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(scope, settings, db_session)


router.include_router(system_settings_router)
router.include_router(record_tools_settings_router)

from typing import Annotated

from fastapi import APIRouter, Body, Path

from adapters.dependencies import DatabaseSessionDep, WithPermission
from entities.role import Permission
from entities.settings import (
    AppSettingsScope,
    SettingsJsonSchema,
    SettingsSchema,
    TaskSettingsScope,
)
from settings.models import AppSettingsSchemas, TaskSettingsSchemas

from . import service

router = APIRouter(prefix="/settings")

app_settings_router = APIRouter(
    prefix="/app",
    tags=["App Settings"],
    dependencies=[WithPermission(Permission.ManageAppSettings)],
)
tasks_settings_router = APIRouter(
    prefix="/tasks",
    tags=["Task Settings"],
    dependencies=[WithPermission(Permission.ManageTaskSettings)],
)


@app_settings_router.get("/{scope}/schema", response_model=SettingsJsonSchema)
async def get_app_settings_schema(scope: Annotated[AppSettingsScope, Path()]):
    return service.get_settings_schema(scope)


@app_settings_router.get("/{scope}", response_model=AppSettingsSchemas)
async def get_app_settings(
    scope: Annotated[AppSettingsScope, Path()],
    db_session: DatabaseSessionDep,
):
    return service.get_settings(scope, db_session)


@app_settings_router.post("/{scope}", response_model=AppSettingsSchemas)
async def set_app_settings(
    scope: Annotated[AppSettingsScope, Path()],
    settings: Annotated[AppSettingsSchemas, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(scope, settings, db_session)


@tasks_settings_router.get(
    "/{scope}/schema", response_model=SettingsJsonSchema
)
async def get_task_settings_schema(
    scope: Annotated[TaskSettingsScope, Path()],
):
    return service.get_settings_schema(scope)


@tasks_settings_router.get("/{scope}", response_model=TaskSettingsSchemas)
async def get_task_settings(
    scope: Annotated[TaskSettingsScope, Path()],
    db_session: DatabaseSessionDep,
):
    return service.get_settings(scope, db_session)


@tasks_settings_router.post("/{scope}", response_model=TaskSettingsSchemas)
async def set_task_settings(
    scope: Annotated[TaskSettingsScope, Path()],
    settings: Annotated[TaskSettingsSchemas, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(scope, settings, db_session)


router.include_router(app_settings_router)
router.include_router(tasks_settings_router)

from typing import Annotated

from fastapi import APIRouter, Body

from adapters.dependencies import DatabaseSessionDep, WithPermission
from catalog_records.models import ProcessRecordsSettings
from entities.role import Permission
from entities.settings import SettingsScope
from maintenance.models import MaintenanceSettings
from settings.models import (
    AuthorityLinkingSettings,
    CatalogSettings,
    ComparisonSettings,
    TaskSettings,
    ValidationSettings,
)

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


@system_settings_router.get("/catalog", response_model=CatalogSettings)
async def get_catalog_settings(
    db_session: DatabaseSessionDep,
):
    return service.get_settings(SettingsScope.Catalog, db_session)


@system_settings_router.post("/catalog", response_model=CatalogSettings)
async def set_catalog_settings(
    settings: Annotated[CatalogSettings, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(SettingsScope.Catalog, settings, db_session)


@system_settings_router.get("/tasks", response_model=TaskSettings)
async def get_task_settings(
    db_session: DatabaseSessionDep,
):
    return service.get_settings(SettingsScope.Tasks, db_session)


@system_settings_router.post("/tasks", response_model=TaskSettings)
async def set_task_settings(
    settings: Annotated[TaskSettings, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(SettingsScope.Tasks, settings, db_session)


@record_tools_settings_router.get("/authority-linkers", response_model=AuthorityLinkingSettings)
async def get_authority_linking_settings(
    db_session: DatabaseSessionDep,
):
    return service.get_settings(SettingsScope.AuthorityLinking, db_session)


@record_tools_settings_router.post("/authority-linkers", response_model=AuthorityLinkingSettings)
async def set_authority_linking_settings(
    settings: Annotated[AuthorityLinkingSettings, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(SettingsScope.AuthorityLinking, settings, db_session)


@record_tools_settings_router.get("/comparators", response_model=ComparisonSettings)
async def get_comparison_settings(
    db_session: DatabaseSessionDep,
):
    return service.get_settings(SettingsScope.Comparison, db_session)


@record_tools_settings_router.post("/comparators", response_model=ComparisonSettings)
async def set_comparison_settings(
    settings: Annotated[ComparisonSettings, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(SettingsScope.Comparison, settings, db_session)


@record_tools_settings_router.get("/validators", response_model=ValidationSettings)
async def get_validation_settings(
    db_session: DatabaseSessionDep,
):
    return service.get_settings(SettingsScope.Validation, db_session)


@record_tools_settings_router.post("/validators", response_model=ValidationSettings)
async def set_validation_settings(
    settings: Annotated[ValidationSettings, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(SettingsScope.Validation, settings, db_session)


@record_tools_settings_router.get("/process-records", response_model=ProcessRecordsSettings)
async def get_process_records_settings(
    db_session: DatabaseSessionDep,
):
    return service.get_settings(SettingsScope.ProcessRecords, db_session)


@record_tools_settings_router.post("/process-records", response_model=ProcessRecordsSettings)
async def set_process_records_settings(
    settings: Annotated[ProcessRecordsSettings, Body()],
    db_session: DatabaseSessionDep,
):
    return service.set_settings(SettingsScope.ProcessRecords, settings, db_session)


@system_settings_router.get("/maintenance", response_model=MaintenanceSettings)
async def get_maintenance_settings(
    db_session: DatabaseSessionDep,
):
    return service.get_settings(SettingsScope.Maintenance, db_session)


@system_settings_router.post("/maintenance", response_model=MaintenanceSettings)
async def set_maintenance_settings(
    settings: Annotated[MaintenanceSettings, Body()],
    db_session: DatabaseSessionDep,
):
    saved = service.set_settings(SettingsScope.Maintenance, settings, db_session)
    from maintenance.schedule import sync_redbeat_schedule

    sync_redbeat_schedule(settings)
    return saved


router.include_router(system_settings_router)
router.include_router(record_tools_settings_router)

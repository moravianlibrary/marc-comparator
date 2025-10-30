from typing import Annotated

from fastapi import APIRouter, Body

from adapters.dependencies import DatabaseSessionDep, IndexerSessionDep
from auth.service import CurrentUser
from entities.settings import SettingsSchema
from entities.task import TaskSchema

from . import service
from .models import ComparisonSettings, ComparisonTaskData

router = APIRouter(prefix="/comparison", tags=["Comparison"])


@router.get("/settings-schema", response_model=SettingsSchema)
async def get_linking_settings_schema():
    return ComparisonSettings.model_json_schema()


@router.get("/settings", response_model=ComparisonSettings)
async def get_linking_settings(db_session: DatabaseSessionDep):
    return service.get_settings(db_session)


@router.post("/settings", response_model=ComparisonSettings)
async def set_linking_settings(
    settings: ComparisonSettings, db_session: DatabaseSessionDep
):
    return service.set_settings(settings, db_session)


@router.post("/task", response_model=TaskSchema)
async def fetch_record(
    data: Annotated[ComparisonTaskData, Body(...)],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.compare(data, current_user.user_id, db_session)

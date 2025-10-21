from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.security import OAuth2PasswordRequestForm

from auth.service import CurrentUser
from catalog.models import FetchRecordData, SyncRecordsData
from entities.task import TaskSchema
from adapters.dependencies import DatabaseSessionDep, IndexerSessionDep

from . import service

router = APIRouter(prefix="/catalog", tags=["catalog"])

OAuthFormData = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/fetch", response_model=TaskSchema)
async def fetch_record(
    data: Annotated[FetchRecordData, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.fetch_record(data, current_user.user_id, db_session)


@router.post("/sync", response_model=TaskSchema)
async def sync_records(
    data: Annotated[SyncRecordsData, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.sync_records(data, current_user.user_id, db_session)

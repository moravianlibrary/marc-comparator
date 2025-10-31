from typing import Annotated

from fastapi import APIRouter, Body

from adapters.dependencies import (
    DatabaseSessionDep,
    IndexerSessionDep,
    WithPermission,
)
from adapters.indexer import IndexerRequest, IndexerResponse
from auth.service import CurrentUser
from catalog_records.models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    SyncRecordsData,
)
from entities.role import Permission
from entities.task import TaskSchema

from . import service

router = APIRouter(prefix="/catalog-records", tags=["Catalog Records"])


@router.post(
    "/search",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=IndexerResponse,
)
async def search_records(
    request: Annotated[IndexerRequest, Body()],
    _: IndexerSessionDep,
):
    return await service.search_records(request)


@router.post(
    "/fetch",
    dependencies=[WithPermission(Permission.AddRecords)],
    response_model=TaskSchema,
)
async def fetch_record(
    data: Annotated[FetchRecordData, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.fetch_record(data, current_user.user_id, db_session)


@router.post(
    "/fetch-batch",
    dependencies=[WithPermission(Permission.AddRecords)],
    response_model=TaskSchema,
)
async def fetch_batch_of_records(
    data: Annotated[FetchBatchOfRecordsData, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.fetch_batch_of_records(
        data, current_user.user_id, db_session
    )


@router.post(
    "/sync",
    dependencies=[WithPermission(Permission.SyncRecordsFromCatalog)],
    response_model=TaskSchema,
)
async def sync_records(
    data: Annotated[SyncRecordsData, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.sync_records(data, current_user.user_id, db_session)

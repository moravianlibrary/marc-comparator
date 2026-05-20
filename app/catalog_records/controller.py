from typing import Annotated

from fastapi import APIRouter, Body
from marcdantic import MarcRecord

from adapters.dependencies import DatabaseSessionDep, WithPermission
from adapters.indexer import IndexerQuery
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .facets import get_facets, get_facets_preview
from .models import (
    FacetsPreviewRequest,
    FacetsPreviewResponse,
    FacetsRequest,
    FacetsResponse,
    FetchBatchOfRecordsData,
    FetchRecordData,
    SearchRecordsRequest,
    SearchRecordsResponse,
    SetRecordsVisibilityData,
    SyncRecordsData,
)
from .search import search_records as pg_search_records

router = APIRouter(prefix="/catalog-records", tags=["Catalog Records"])


@router.post(
    "/search",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=SearchRecordsResponse,
)
async def search_records(
    request: Annotated[SearchRecordsRequest, Body()],
    db_session: DatabaseSessionDep,
):
    return pg_search_records(request, db_session)


@router.post(
    "/facets",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=FacetsResponse,
)
async def get_record_facets(
    request: Annotated[FacetsRequest, Body()],
):
    return get_facets(request)


@router.post(
    "/facets-preview",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=FacetsPreviewResponse,
)
async def get_record_facets_preview(
    request: Annotated[FacetsPreviewRequest, Body()],
):
    return get_facets_preview(request)


@router.get(
    "/{base}/{system_number}/marc",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=MarcRecord,
)
async def get_marc_record(
    base: str,
    system_number: str,
    db_session: DatabaseSessionDep,
):
    return service.get_marc_record(base, system_number, db_session)


@router.post(
    "/fetch",
    dependencies=[WithPermission(Permission.AddRecords)],
    response_model=TaskSchema,
)
async def fetch_record(
    data: Annotated[FetchRecordData, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
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
):
    return await service.sync_records(data, current_user.user_id, db_session)


@router.post(
    "/reindex",
    dependencies=[WithPermission(Permission.RunRecordTasks)],
    response_model=TaskSchema,
)
async def reindex_records(
    query: Annotated[IndexerQuery, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.reindex_records(
        query, current_user.user_id, db_session
    )


@router.post(
    "/visibility",
    dependencies=[WithPermission(Permission.RunRecordTasks)],
    response_model=TaskSchema,
)
async def set_records_visibility(
    data: Annotated[SetRecordsVisibilityData, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.set_records_visibility(
        data, current_user.user_id, db_session
    )


@router.post(
    "/process",
    dependencies=[WithPermission(Permission.RunRecordTasks)],
    response_model=TaskSchema,
)
async def process_records(
    data: Annotated[IndexerQuery, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.process_records(
        data, current_user.user_id, db_session
    )

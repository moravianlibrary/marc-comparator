from typing import Annotated

from fastapi import APIRouter, Body
from marcdantic import MarcRecord

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser, get_current_user_data
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .facets import get_facets, get_facets_preview
from .models import (
    CreateReviewRequest,
    FacetsPreviewRequest,
    FacetsPreviewResponse,
    FacetsRequest,
    FacetsResponse,
    FetchBatchOfRecordsData,
    FetchRecordData,
    RecordFilter,
    RecordReviewsResponse,
    SearchRecordsRequest,
    SearchRecordsResponse,
    SyncRecordsData,
)
from .search import search_records as pg_search_records

router = APIRouter(prefix="/catalog-records", tags=["Catalog Records"])


@router.post(
    "/search",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=SearchRecordsResponse,
)
def search_records(
    request: Annotated[SearchRecordsRequest, Body()],
    db_session: DatabaseSessionDep,
):
    return pg_search_records(request, db_session)


@router.post(
    "/facets",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=FacetsResponse,
)
def get_record_facets(
    request: Annotated[FacetsRequest, Body()],
    db_session: DatabaseSessionDep,
):
    return get_facets(request, db_session)


@router.post(
    "/facets-preview",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=FacetsPreviewResponse,
)
def get_record_facets_preview(
    request: Annotated[FacetsPreviewRequest, Body()],
    db_session: DatabaseSessionDep,
):
    return get_facets_preview(request, db_session)


@router.get(
    "/{base}/{system_number}/marc",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=MarcRecord,
)
def get_marc_record(
    base: str,
    system_number: str,
    db_session: DatabaseSessionDep,
):
    return service.get_marc_record(base, system_number, db_session)


@router.get(
    "/{base}/{system_number}/comparisons",
    dependencies=[WithPermission(Permission.ReadRecords)],
)
def get_comparisons(
    base: str,
    system_number: str,
    db_session: DatabaseSessionDep,
):
    return service.get_comparisons(base, system_number, db_session)


@router.get(
    "/{base}/{system_number}/validations",
    dependencies=[WithPermission(Permission.ReadRecords)],
)
def get_validations(
    base: str,
    system_number: str,
    db_session: DatabaseSessionDep,
):
    return service.get_validations(base, system_number, db_session)


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
    return await service.fetch_batch_of_records(data, current_user.user_id, db_session)


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


@router.get(
    "/{base}/{system_number}/reviews",
    dependencies=[WithPermission(Permission.ReadRecords)],
    response_model=RecordReviewsResponse,
)
def get_reviews(
    base: str,
    system_number: str,
    db_session: DatabaseSessionDep,
):
    return service.get_reviews(base, system_number, db_session)


@router.post(
    "/{base}/{system_number}/review",
    dependencies=[WithPermission(Permission.ReviewRecords)],
)
def create_review(
    base: str,
    system_number: str,
    data: Annotated[CreateReviewRequest, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return service.create_review(base, system_number, data, current_user.user_id, db_session)


@router.delete(
    "/{base}/{system_number}/review",
    dependencies=[WithPermission(Permission.ReviewRecords)],
)
def delete_review(
    base: str,
    system_number: str,
    aspect_name: str,
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    user_data = get_current_user_data(current_user, db_session)
    can_manage = Permission.ManageReviews in user_data.permissions
    return service.delete_review(
        base, system_number, aspect_name, current_user.user_id, can_manage, db_session
    )


@router.post(
    "/process",
    dependencies=[WithPermission(Permission.ProcessRecords)],
    response_model=TaskSchema,
)
async def process_records(
    filters: Annotated[RecordFilter, Body()],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.process_records(filters, current_user.user_id, db_session)

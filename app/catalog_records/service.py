from fastapi import HTTPException, status

from adapters.database import DatabaseSession
from adapters.indexer import IndexerRequest, IndexerResponse
from adapters.lock_server import one_at_a_time_lock
from adapters.tasks import enqueue_task
from catalog_records.models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    SyncRecordsData,
)
from entities.catalog_record import CatalogRecord
from entities.task import Task, TaskSchema, TaskType


async def search_records(request: IndexerRequest) -> IndexerResponse:
    return CatalogRecord.search(request)


async def fetch_record(
    data: FetchRecordData, created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name=f"Fetch catalog record {data.base}-{data.system_number}",
            type=TaskType.FetchRecord,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )


async def fetch_batch_of_records(
    data: FetchBatchOfRecordsData, created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    count_bases = len(set(pb.base for pb in data.per_base))
    count_records = sum(len(pb.system_numbers) for pb in data.per_base)

    return await enqueue_task(
        Task(
            name=(
                f"Fetching batch of {count_records} catalog records "
                f"from {count_bases} bases"
            ),
            type=TaskType.FetchBatchOfRecords,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )


async def sync_records(
    data: SyncRecordsData, created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    # Try to acquire lock to prevent concurrent sync for the same base
    lock_key = f"catalog_sync_{data.base}"
    lock_blocking_timeout = 1
    with one_at_a_time_lock(
        lock_key, blocking_timeout=lock_blocking_timeout
    ) as acquired:
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sync task is already running for base {data.base}.",
            )

        return await enqueue_task(
            Task(
                name=f"Sync records from catalog for base {data.base}",
                type=TaskType.SyncRecords,
                created_by=created_by,
                data=data.model_dump(),
            ),
            db_session,
        )

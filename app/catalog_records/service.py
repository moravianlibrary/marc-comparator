from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.indexer import IndexerQuery, IndexerRequest, IndexerResponse
from adapters.lock_server import one_at_a_time_lock
from adapters.tasks import enqueue_task
from entities.catalog_record import CatalogRecord
from entities.task import Task, TaskSchema, TaskType

from .exceptions import (
    CatalogRecordNotFoundException,
    SyncTaskAlreadyRunningException,
)
from .models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    SetRecordsHiddenStateData,
    SyncRecordsData,
)


async def search_records(request: IndexerRequest) -> IndexerResponse:
    return await CatalogRecord.search(request)


def get_marc_record(
    base: str, system_number: str, db_session: DatabaseSession
) -> MarcRecord:
    catalog_record = CatalogRecord.find_by_base_and_system_number(
        db_session, base, system_number
    )

    if not catalog_record or catalog_record.deleted:
        raise CatalogRecordNotFoundException(base, system_number)

    return catalog_record.record


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
            raise SyncTaskAlreadyRunningException(data.base)

        return await enqueue_task(
            Task(
                name=f"Sync records from catalog for base {data.base}",
                type=TaskType.SyncRecords,
                created_by=created_by,
                data=data.model_dump(mode="json"),
            ),
            db_session,
        )


async def reindex_records(
    query: IndexerQuery, created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Reindex catalog records",
            type=TaskType.ReindexRecords,
            created_by=created_by,
            data=query.model_dump(),
        ),
        db_session,
    )


async def set_records_hidden_state(
    data: SetRecordsHiddenStateData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name=f"{'Hide' if data.hide else 'Unhide'} catalog records",
            type=TaskType.SetRecordsHiddenState,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

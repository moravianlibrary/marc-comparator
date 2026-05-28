from fastapi import HTTPException
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.lock_server import one_at_a_time_lock
from adapters.tasks import enqueue_task
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.record_review import RecordReview, ReviewStatus
from entities.task import Task, TaskSchema, TaskType
from entities.validation import Validation

from .exceptions import (
    CatalogRecordNotFoundException,
    SyncTaskAlreadyRunningException,
)
from .models import (
    CreateReviewRequest,
    FetchBatchOfRecordsData,
    FetchRecordData,
    RecordFilter,
    RecordReviewsResponse,
    ReviewResponse,
    SyncRecordsData,
)


def get_marc_record(
    base: str, system_number: str, db_session: DatabaseSession
) -> MarcRecord:
    catalog_record = CatalogRecord.find_by_base_and_system_number(
        db_session, base, system_number
    )

    if not catalog_record or catalog_record.deleted:
        raise CatalogRecordNotFoundException(base, system_number)

    return catalog_record.get_record(db_session)


def get_comparisons(
    base: str, system_number: str, db_session: DatabaseSession
) -> list[dict]:
    record_id = CatalogRecord.generate_id(base, system_number)
    comparisons = (
        db_session.query(Comparison)
        .filter_by(main_record_id=record_id)
        .all()
    )
    return [
        {
            "comparator": c.comparator,
            "base": c.base,
            "other_record_id": c.other_record_id,
            "result": c.result,
        }
        for c in comparisons
    ]


def get_validations(
    base: str, system_number: str, db_session: DatabaseSession
) -> list[dict]:
    record_id = CatalogRecord.generate_id(base, system_number)
    validations = (
        db_session.query(Validation)
        .filter_by(catalog_record_id=record_id)
        .all()
    )
    return [
        {
            "id": v.id,
            "validator": v.validator,
            "result": v.result,
        }
        for v in validations
    ]


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
    ) as lock:
        if not lock:
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


def _review_to_response(review: RecordReview) -> ReviewResponse:
    reviewer = review.reviewer
    return ReviewResponse(
        id=str(review.id),
        record_id=review.record_id,
        aspect_name=review.aspect_name,
        note=review.note,
        reviewed_by=str(review.reviewed_by),
        reviewer_name=(
            f"{reviewer.first_name} {reviewer.last_name}"
            if reviewer else None
        ),
        reviewed_at=review.reviewed_at,
        status=review.status,
    )


def get_reviews(
    base: str, system_number: str, db_session: DatabaseSession
) -> RecordReviewsResponse:
    record_id = CatalogRecord.generate_id(base, system_number)
    reviews = (
        db_session.query(RecordReview)
        .filter_by(record_id=record_id)
        .order_by(RecordReview.reviewed_at.desc())
        .all()
    )
    current = [_review_to_response(r) for r in reviews if r.status == ReviewStatus.Current]
    history = [_review_to_response(r) for r in reviews if r.status != ReviewStatus.Current]
    return RecordReviewsResponse(current=current, history=history)


def create_review(
    base: str,
    system_number: str,
    data: CreateReviewRequest,
    user_id: str,
    db_session: DatabaseSession,
) -> ReviewResponse:
    record_id = CatalogRecord.generate_id(base, system_number)
    record = CatalogRecord.find(db_session, record_id)
    if not record:
        raise CatalogRecordNotFoundException(base, system_number)

    # Supersede any existing current review for this aspect
    RecordReview.supersede_current(db_session, record_id, data.aspect_name)

    review = RecordReview(
        record_id=record_id,
        aspect_name=data.aspect_name,
        note=data.note,
        reviewed_by=user_id,
        status=ReviewStatus.Current,
    )
    review.save(db_session)

    # Update analytics for this record
    from catalog_records.analytics import upsert_records
    upsert_records(db_session, [record_id])

    return _review_to_response(review)


def delete_review(
    base: str,
    system_number: str,
    aspect_name: str,
    user_id: str,
    can_manage: bool,
    db_session: DatabaseSession,
) -> dict:
    record_id = CatalogRecord.generate_id(base, system_number)
    current = RecordReview.find_current(db_session, record_id, aspect_name)
    if not current:
        raise HTTPException(status_code=404, detail="No current review found")

    if not can_manage and str(current.reviewed_by) != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own reviews")

    current.status = ReviewStatus.Superseded
    db_session.commit()

    # Update analytics for this record
    from catalog_records.analytics import upsert_records
    upsert_records(db_session, [record_id])

    return {"ok": True}


async def process_records(
    filters: RecordFilter, created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Process catalog records",
            type=TaskType.ProcessRecords,
            created_by=created_by,
            data=filters.model_dump(),
        ),
        db_session,
    )

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from adapters.clickhouse import insert, query
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.validation import Validation

logger = logging.getLogger(__name__)

TABLE = "catalog_records_analytics"
BATCH_SIZE = 1000


def get_last_sync_timestamp() -> datetime | None:
    """Get the latest updated_at from ClickHouse to know where sync left off."""
    rows = query(f"SELECT max(updated_at) AS ts FROM {TABLE}")
    if rows and rows[0]["ts"]:
        ts = rows[0]["ts"]
        if isinstance(ts, str):
            return datetime.fromisoformat(ts)
        return ts
    return None


def sync_records(db: Session) -> int:
    """Sync changed records from PG to ClickHouse. Returns count synced."""
    last_sync = get_last_sync_timestamp()

    q = db.query(CatalogRecord).options(
        joinedload(CatalogRecord.authority_links),
        joinedload(CatalogRecord.comparisons),
        joinedload(CatalogRecord.validations),
    )

    if last_sync:
        q = q.filter(CatalogRecord.updated_at > last_sync)

    q = q.order_by(CatalogRecord.updated_at)

    count = 0
    batch = []
    columns = [
        "id", "base", "system_number", "type_of_record", "bibliographic_level",
        "is_deleted", "is_hidden", "is_processed",
        "authority_link_linkers", "authority_link_bases",
        "comparators", "comparison_bases", "match_qualities", "overall_scores",
        "field_explanations",
        "validators", "validation_statuses", "validation_target_tags",
        "latest_sync", "latest_transaction", "processed_at",
        "updated_at",
    ]

    for record in q.yield_per(BATCH_SIZE):
        row = _denormalize(record)
        batch.append(row)
        count += 1

        if len(batch) >= BATCH_SIZE:
            insert(TABLE, batch, columns)
            batch = []

    if batch:
        insert(TABLE, batch, columns)

    if count > 0:
        logger.info(f"Synced {count} records to ClickHouse")
    return count


def _denormalize(record: CatalogRecord) -> list:
    """Convert a CatalogRecord + relationships into a flat ClickHouse row."""
    al_linkers = [al.linker for al in record.authority_links]
    al_bases = [al.base for al in record.authority_links]

    comparators = [c.comparator for c in record.comparisons]
    # Extract comparison base from other_record_id (format: "{base}-{system_number}")
    comp_bases = []
    for c in record.comparisons:
        parts = c.other_record_id.split("-", 1)
        comp_bases.append(parts[0] if parts else "")

    match_qualities = [c.match_quality.value for c in record.comparisons]
    overall_scores = [c.overall_score for c in record.comparisons]

    # Collect unique field explanations across all comparisons
    field_explanations = set()
    for c in record.comparisons:
        fr_list = c.record_result.field_results
        if fr_list:
            for fr in fr_list:
                if fr.explanation:
                    field_explanations.add(fr.explanation)

    validators = [v.validator for v in record.validations]
    validation_statuses = []
    validation_target_tags = set()
    for v in record.validations:
        result = v._result or {}
        validation_statuses.append(result.get("status", ""))
        target = result.get("target", {})
        if target and target.get("tag"):
            validation_target_tags.add(target["tag"])

    return [
        record.id,
        record.base,
        record.system_number,
        record.type_of_record or "",
        record.bibliographic_level or "",
        int(record.deleted),
        int(record.hidden),
        int(record.processed_at is not None),
        al_linkers,
        al_bases,
        comparators,
        comp_bases,
        match_qualities,
        overall_scores,
        list(field_explanations),
        validators,
        validation_statuses,
        list(validation_target_tags),
        record.latest_sync,
        record.latest_transaction,
        record.processed_at,
        record.updated_at or datetime.now(timezone.utc),
    ]

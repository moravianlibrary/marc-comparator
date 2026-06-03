import hashlib
import json
from collections import defaultdict

from aleph_nought import RecordStatus
from marcdantic import MarcRecord

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from authority_linking.tasks import (
    LinkActionResult,
    find_best_link_for_record,
    handle_catalog_record_link_action,
    load_authority_linkers,
)
from catalog_records.models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    ProcessRecordsSettings,
    RecordFilter,
    SyncRecordsData,
)
from catalog_records.search import build_filtered_query
from comparison.tasks import handle_catalog_record_comparison, load_comparator
from config import config
from entities.catalog_record import CatalogRecord
from entities.record_review import RecordReview
from entities.result_snapshot import ResultSnapshot
from entities.settings import Settings, SettingsScope
from validation.tasks import handle_catalog_record_validation, load_validators


class AlephError(Exception):
    pass


def _compute_result_hashes(db_session, record_id: str) -> dict[str, tuple[str, list[dict]]]:
    """Compute per-aspect content hashes from current comparisons and validations.

    Returns {aspect_name: (hex_hash, [result_dicts])} so we can snapshot old data
    if the hash changes after reprocessing.
    """
    from entities.comparison import Comparison
    from entities.validation import Validation

    hashes: dict[str, tuple[str, list[dict]]] = {}

    comparisons = db_session.query(Comparison).filter_by(main_record_id=record_id).all()
    _hash_grouped_results(comparisons, "comparator", hashes)

    validations = db_session.query(Validation).filter_by(catalog_record_id=record_id).all()
    _hash_grouped_results(validations, "validator", hashes)

    return hashes


def _hash_grouped_results(
    entities, group_key_attr: str, out: dict[str, tuple[str, list[dict]]]
) -> None:
    """Group entities by an attribute, hash each group's results, and store in `out`."""
    by_key: dict[str, list[dict]] = {}
    for e in entities:
        by_key.setdefault(getattr(e, group_key_attr), []).append(e.result)
    for aspect, results in by_key.items():
        canonical = json.dumps(results, sort_keys=True, ensure_ascii=False)
        out[aspect] = (hashlib.sha256(canonical.encode()).hexdigest(), results)


def _handle_result_changes(
    db_session, record_id: str, old_hashes: dict[str, tuple[str, list[dict]]]
) -> None:
    """Compare old vs new result hashes. Snapshot old data and outdate reviews where changed."""
    new_hashes = _compute_result_hashes(db_session, record_id)

    for aspect_name, (old_hash, old_data) in old_hashes.items():
        new_entry = new_hashes.get(aspect_name)
        new_hash = new_entry[0] if new_entry else None

        if new_hash != old_hash:
            version = ResultSnapshot.next_version(db_session, record_id, aspect_name)
            snapshot = ResultSnapshot(
                record_id=record_id,
                aspect_name=aspect_name,
                version=version,
                data=old_data,
            )
            db_session.add(snapshot)
            RecordReview.outdate_current(db_session, record_id, aspect_name)

    # Also outdate reviews for aspects that are new (didn't exist before)
    for aspect_name in new_hashes:
        if aspect_name not in old_hashes:
            RecordReview.outdate_current(db_session, record_id, aspect_name)


def save_record_metadata(
    ctx: ManagedTask,
    base: str,
    system_number: str,
    record: MarcRecord,
    catalog_record: CatalogRecord | None = None,
) -> CatalogRecord:
    """Save catalog record metadata (without MARC bytes) to the database.

    When *catalog_record* is passed, it is reused instead of querying again.
    """
    if catalog_record is None:
        catalog_record = CatalogRecord.find_by_base_and_system_number(
            ctx.db_session, base, system_number
        )

    if catalog_record:
        catalog_record.deleted = False
        catalog_record.latest_sync = config.timestamp
    else:
        catalog_record = CatalogRecord(
            base=base,
            system_number=system_number,
        )

    catalog_record.type_of_record = record.leader_selector.type_of_record
    catalog_record.bibliographic_level = record.leader_selector.bibliographic_level
    catalog_record.update_search_text_from(record)
    catalog_record.save(ctx.db_session, commit=False)

    return catalog_record


def save_record_snippet(
    ctx: ManagedTask,
    base: str,
    system_number: str,
    record: MarcRecord,
) -> CatalogRecord:
    """Save catalog record metadata and MARC bytes (single-record upsert)."""
    from adapters.marc_sectors import read_marc, upsert_record_in_sector

    old_marc = read_marc(ctx.db_session, base, system_number)
    catalog_record = save_record_metadata(ctx, base, system_number, record)
    upsert_record_in_sector(ctx.db_session, base, system_number, record._marc)

    if old_marc is not None and old_marc != record._marc:
        catalog_record.processed_at = None
        RecordReview.outdate_current(ctx.db_session, catalog_record.id)

    return catalog_record


async def fetch_record_task(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = FetchRecordData.model_validate(ctx.task.data)
        base = data.base
        system_number = data.system_number

        client = AlephClientRegistry.get(base)
        if not client.OAI.is_available():
            ctx.logger.error(f"OAI service for {base} is not available")
            return

        record = client.OAI.get_record(system_number)

        if record is None:
            ctx.logger.error(f"Record with system number '{system_number}' not found")
            return

        save_record_snippet(ctx, base, system_number, record)

        ctx.logger.info(f"Finished fetching record {base}-{system_number}")


async def fetch_batch_of_records_task(task_id: str) -> None:
    from adapters.marc_sectors import SectorBuffer

    async with ManagedTask(task_id=task_id) as ctx:
        data = FetchBatchOfRecordsData.model_validate(ctx.task.data)
        ctx.total = sum(len(d.system_numbers) for d in data.per_base)

        buffer = SectorBuffer(lambda: ctx.db_session)
        ctx.before_commit = buffer.flush_all

        for fetch_base_data in data.per_base:
            base = fetch_base_data.base
            client = AlephClientRegistry.get(base)

            if not client.OAI.is_available():
                ctx.logger.error(f"OAI service for {base} is not available")
                continue

            for system_number in fetch_base_data.system_numbers:
                try:
                    record = client.OAI.get_record(system_number)

                    if record is None:
                        ctx.logger.error(
                            f"Record with system number '{system_number}' "
                            f"not found in base '{base}'"
                        )
                        handle_batch_progress_snippet(ctx)
                        continue

                    from adapters.marc_sectors import read_marc

                    existing = CatalogRecord.find_by_base_and_system_number(
                        ctx.db_session, base, system_number
                    )
                    old_marc = read_marc(ctx.db_session, base, system_number) if existing else None
                    catalog_record = save_record_metadata(ctx, base, system_number, record, existing)
                    buffer.add(base, system_number, record._marc)

                    if old_marc is not None and old_marc != record._marc:
                        catalog_record.processed_at = None
                        RecordReview.outdate_current(ctx.db_session, catalog_record.id)

                    handle_batch_progress_snippet(ctx)

                except Exception as e:
                    ctx.db_session.rollback()
                    ctx.logger.error(f"Failed processing record {system_number}:\n{e}")
                    handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(
            f"Finished fetching batch of records, total records processed: {ctx.progress}"
        )


async def records_sync_task(task_id: str, lock_key: str, lock_blocking_timeout: int):
    from adapters.marc_sectors import SectorBuffer

    async with ManagedTask(
        task_id=task_id,
        lock_key=lock_key,
        lock_blocking_timeout=lock_blocking_timeout,
    ) as ctx:
        data = SyncRecordsData.model_validate(ctx.task.data)

        base = data.base
        from_date = data.from_date.strftime("%Y-%m-%dT%H:%M:%SZ") if data.from_date else None

        if from_date is None:
            ctx.logger.info(f"Starting catalog sync for base '{base}'")
        else:
            ctx.logger.info(f"Starting catalog sync for base '{base}' from date '{from_date}'")

        client = AlephClientRegistry.get(base)
        if not client.OAI.is_available():
            ctx.logger.error(f"OAI service for {base} is not available")
            return

        buffer = SectorBuffer(lambda: ctx.db_session)
        ctx.before_commit = buffer.flush_all

        for base, system_number, status, record in client.OAI.list_records(from_date, None):
            try:
                if status == RecordStatus.Failed:
                    ctx.logger.error(f"Failed fetching record {base}-{system_number}.")
                    continue

                catalog_record = CatalogRecord.find_by_base_and_system_number(
                    ctx.db_session, base, system_number
                )

                if status == RecordStatus.Deleted and catalog_record is None:
                    pass

                elif status == RecordStatus.Deleted and catalog_record:
                    catalog_record.latest_sync = config.timestamp
                    catalog_record.deleted = True
                    ctx.logger.info(f"Marking record {base}-{system_number} as deleted.")

                elif not record:
                    ctx.logger.error(f"Record {base}-{system_number} has no MARC data.")

                else:
                    from adapters.marc_sectors import read_marc

                    old_marc = read_marc(ctx.db_session, base, system_number) if catalog_record else None
                    cr = save_record_metadata(ctx, base, system_number, record, catalog_record)
                    buffer.add(base, system_number, record._marc)

                    if old_marc is not None and old_marc != record._marc:
                        cr.processed_at = None
                        RecordReview.outdate_current(ctx.db_session, cr.id)

                handle_batch_progress_snippet(ctx)

            except Exception as e:
                ctx.db_session.rollback()
                ctx.logger.error(f"Failed processing record {system_number}:\n{e}")
                handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(f"Finished catalog sync, total records processed: {ctx.progress}")


async def process_records(task_id: str) -> None:
    """
    Process catalog records: link to authorities, compare with linked records,
    validate, and mark as processed.
    """
    async with ManagedTask(task_id=task_id) as ctx:
        settings: ProcessRecordsSettings | None = Settings.get(
            ctx.db_session,
            SettingsScope.ProcessRecords,
            ProcessRecordsSettings,
        )

        if not settings:
            ctx.logger.error("Process records settings not found")
            return

        filters = RecordFilter.model_validate(ctx.task.data)
        ctx.logger.info("Starting processing of catalog records")

        authority_linkers = load_authority_linkers(ctx.db_session, settings.authority_linkers)
        if not authority_linkers:
            ctx.logger.error("Authority linkers could not be initialized")
            return

        comparator = load_comparator(ctx.db_session)
        if not comparator:
            ctx.logger.error("Comparator could not be initialized")
            return

        validator_instances = load_validators(ctx.db_session, settings.validators, ctx.logger)
        if not validator_instances:
            ctx.logger.error("Validators could not be initialized")
            return

        counters: defaultdict[LinkActionResult, int] = defaultdict(int)

        record_ids = [
            r.id
            for r in build_filtered_query(ctx.db_session, filters)
            .with_entities(CatalogRecord.id)
            .all()
        ]
        ctx.total = len(record_ids)

        batch_size = 1000
        for i in range(0, len(record_ids), batch_size):
            batch_ids = record_ids[i : i + batch_size]
            records = (
                ctx.db_session.query(CatalogRecord).filter(CatalogRecord.id.in_(batch_ids)).all()
            )
            for catalog_record in records:
                try:
                    # Capture result hashes before reprocessing
                    old_hashes = _compute_result_hashes(ctx.db_session, catalog_record.id)

                    marc_record = catalog_record.get_record(ctx.db_session)

                    for target_base in settings.target_bases:
                        if target_base == catalog_record.base:
                            continue
                        found_link, linker_instance = await find_best_link_for_record(
                            catalog_record,
                            authority_linkers,
                            target_base,
                            marc_record,
                            ctx.logger,
                        )
                        results = handle_catalog_record_link_action(
                            ctx.db_session,
                            catalog_record,
                            found_link,
                            linker_instance,
                            target_base,
                        )
                        for result in results:
                            counters[result] += 1

                    ctx.db_session.refresh(catalog_record)

                    for authority_link in catalog_record.authority_links:
                        await handle_catalog_record_comparison(
                            ctx.db_session,
                            comparator,
                            ctx.logger,
                            authority_link.base,
                            catalog_record,
                        )

                    for validator_instance in validator_instances:
                        await handle_catalog_record_validation(
                            ctx.db_session,
                            catalog_record,
                            validator_instance,
                        )

                    _handle_result_changes(ctx.db_session, catalog_record.id, old_hashes)

                    catalog_record.processed_at = config.timestamp
                    catalog_record.save(ctx.db_session, commit=False)

                    handle_batch_progress_snippet(ctx)

                except ValueError as e:
                    ctx.logger.warning(f"Skipping record {catalog_record.id}: {e}")
                    handle_batch_progress_snippet(ctx)

                except Exception as e:
                    ctx.db_session.rollback()
                    ctx.logger.error(f"Failed processing record {catalog_record.id}:\n{e}")
                    handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)
        ctx.logger.info(f"Finished processing records, total records processed: {ctx.progress}")
        ctx.logger.info(
            "Summary of link actions: %s",
            {k.value: v for k, v in counters.items()},
        )

import hashlib
import json
from collections import defaultdict
from collections.abc import Sequence

from aleph_nought import RecordStatus
from marc_comparator.comparators import RecordComparisonResult
from marcdantic import MarcRecord
from sqlalchemy.orm import joinedload

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.marc_sectors import SectorBuffer, read_marc_many
from adapters.pipelining import chunks, read_ahead
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from authority_linking.tasks import (
    LINK_PREFETCH_WINDOW,
    AuthorityLinkingFailed,
    LinkActionResult,
    announce_link_window,
    announce_window,
    find_best_link_for_record,
    handle_catalog_record_link_action,
    load_authority_linkers,
    load_confident_threshold,
    prefetch_linked_authority_marc,
    windows,
)
from catalog_records.models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    ProcessRecordsSettings,
    RecordFilter,
    SyncRecordsData,
)
from catalog_records.search import build_filtered_query
from comparison.tasks import (
    handle_catalog_record_comparison,
    load_comparator,
    load_gate_comparator,
)
from config import config
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord
from entities.record_review import RecordReview
from entities.result_snapshot import ResultSnapshot
from entities.settings import Settings, SettingsScope
from entities.validation import stored_results_for
from validation.tasks import handle_catalog_record_validation, load_validators

#: Records held between the catalogue and the loop that stores them.
#:
#: The catalogue serves thirty per request and will not be persuaded to serve
#: more, so this is a few pages: far enough ahead that a fetch is always in
#: flight, near enough that a failure is noticed without a long backlog first.
SYNC_READ_AHEAD = 120

#: Records whose previous MARC is read in one go. Sized like the read-ahead,
#: since a larger window only waits longer before doing any work.
SYNC_WINDOW = 60


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


def _result_hashes_for(
    db_session, record_ids: Sequence[str]
) -> dict[str, dict[str, tuple[str, list[dict]]]]:
    """The same hashes for a window of records, in two queries rather than 2n.

    Every processed record reads its comparisons and validations to see what
    it is about to replace, and asked one record at a time that measured
    2.07 ms against 0.24 ms for the same two hundred records asked together.
    Only the reading is shared; each record is still hashed on its own.
    """

    from entities.comparison import Comparison
    from entities.validation import Validation

    wanted = list(record_ids)
    comparisons: defaultdict[str, list[Comparison]] = defaultdict(list)
    validations: defaultdict[str, list[Validation]] = defaultdict(list)
    if wanted:
        for comparison in (
            db_session.query(Comparison).filter(Comparison.main_record_id.in_(wanted)).all()
        ):
            comparisons[comparison.main_record_id].append(comparison)
        for validation in (
            db_session.query(Validation).filter(Validation.catalog_record_id.in_(wanted)).all()
        ):
            validations[validation.catalog_record_id].append(validation)

    hashes: dict[str, dict[str, tuple[str, list[dict]]]] = {}
    for record_id in wanted:
        for_record: dict[str, tuple[str, list[dict]]] = {}
        _hash_grouped_results(comparisons.get(record_id, []), "comparator", for_record)
        _hash_grouped_results(validations.get(record_id, []), "validator", for_record)
        hashes[record_id] = for_record
    return hashes


def _link_fingerprint(links: Sequence[AuthorityLink]) -> str:
    """What this record's authority links say, as one comparable string.

    Kept apart from the result hashes on purpose: those feed ResultSnapshot
    and outdate a record's reviews, and a link moving is not by itself a
    reason to invalidate somebody's review of a comparison. This exists only
    to answer whether a pass found anything new.
    """

    return json.dumps(
        sorted(
            (link.linker, link.base, link.authority_record_id, link.confidence) for link in links
        ),
        sort_keys=True,
    )


def _link_fingerprints_for(db_session, record_ids: Sequence[str]) -> dict[str, str]:
    """The same for a window, in one query rather than one per record."""

    wanted = list(record_ids)
    by_record: defaultdict[str, list[AuthorityLink]] = defaultdict(list)
    if wanted:
        for link in (
            db_session.query(AuthorityLink).filter(AuthorityLink.main_record_id.in_(wanted)).all()
        ):
            by_record[link.main_record_id].append(link)
    return {record_id: _link_fingerprint(by_record.get(record_id, [])) for record_id in wanted}


def _old_hashes_for(db_session, record_id: str, window_hashes: dict) -> dict:
    """What a record's results looked like before this pass reprocessed it.

    Membership, not truth: a record with nothing to replace yet hashes to an
    empty dict, and asking `window_hashes.get(record_id) or ...` sent every one
    of those back to the database for an answer the window already had. On a
    first pass that is every record, which made the windowed read pure cost.
    """

    if record_id in window_hashes:
        return window_hashes[record_id]
    return _compute_result_hashes(db_session, record_id)


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
) -> bool:
    """Compare old vs new result hashes. Snapshot old data and outdate reviews where changed.

    Returns whether anything actually differed. The caller needs that to know
    whether the pass found anything: results move without the record moving,
    because validators ask Kramerius and linkers ask the dump and knihovny.cz,
    and any of those can answer differently than they did last time.
    """
    return _apply_result_changes(
        db_session, record_id, old_hashes, _compute_result_hashes(db_session, record_id)
    )


def _apply_result_changes(
    db_session,
    record_id: str,
    old_hashes: dict[str, tuple[str, list[dict]]],
    new_hashes: dict[str, tuple[str, list[dict]]],
) -> bool:
    """The comparison itself, given both sides.

    Split out so a window can read every record's new results in two queries
    instead of two per record — the post-pass read was the last thing in the
    processing loop still asked one record at a time.
    """

    changed = False

    for aspect_name, (old_hash, old_data) in old_hashes.items():
        new_entry = new_hashes.get(aspect_name)
        new_hash = new_entry[0] if new_entry else None

        if new_hash != old_hash:
            changed = True
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
            changed = True
            RecordReview.outdate_current(db_session, record_id, aspect_name)

    return changed


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
    from adapters.marc_sectors import marc_bytes_of, read_marc, upsert_record_in_sector

    old_marc = read_marc(ctx.db_session, base, system_number)
    catalog_record = save_record_metadata(ctx, base, system_number, record)
    upsert_record_in_sector(ctx.db_session, base, system_number, marc_bytes_of(record))

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
    from adapters.marc_sectors import SectorBuffer, marc_bytes_of

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
                    catalog_record = save_record_metadata(
                        ctx, base, system_number, record, existing
                    )
                    marc = marc_bytes_of(record)
                    if old_marc != marc:
                        # When they match, storage already holds this record byte
                        # for byte; buffering it would rewrite its whole sector to
                        # arrive at what is already there.
                        buffer.add(base, system_number, marc)

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
    from adapters.marc_sectors import SectorBuffer, marc_bytes_of

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

        # The catalogue serves thirty records per request and decides that
        # itself — every page-size hint it was offered came back badArgument —
        # so the fetching is put on its own thread to run under the writing
        # rather than in front of it.
        incoming = read_ahead(client.OAI.list_records(from_date, None), SYNC_READ_AHEAD)

        for page in chunks(incoming, SYNC_WINDOW):
            # One read of the previous MARC for the whole window: its only job
            # is to spot a record that changed, and asked per record it was the
            # largest thing the sync did after waiting for the catalogue. Keyed
            # by the base each record reports rather than the one asked for, so
            # this reads exactly what the per-record lookup read.
            by_base: defaultdict[str, list[str]] = defaultdict(list)
            for record_base, system_number, _status, _record in page:
                by_base[record_base].append(system_number)
            old_marcs = {
                (record_base, system_number): marc
                for record_base, system_numbers in by_base.items()
                for system_number, marc in read_marc_many(
                    ctx.db_session, record_base, system_numbers
                ).items()
            }

            for record_base, system_number, status, record in page:
                try:
                    if status == RecordStatus.Failed:
                        ctx.logger.error(f"Failed fetching record {record_base}-{system_number}.")
                        continue

                    catalog_record = CatalogRecord.find_by_base_and_system_number(
                        ctx.db_session, record_base, system_number
                    )

                    if status == RecordStatus.Deleted and catalog_record is None:
                        pass

                    elif status == RecordStatus.Deleted and catalog_record:
                        catalog_record.latest_sync = config.timestamp
                        catalog_record.deleted = True
                        ctx.logger.info(f"Marking record {record_base}-{system_number} as deleted.")

                    elif not record:
                        ctx.logger.error(f"Record {record_base}-{system_number} has no MARC data.")

                    else:
                        old_marc = (
                            old_marcs.get((record_base, system_number)) if catalog_record else None
                        )
                        cr = save_record_metadata(
                            ctx, record_base, system_number, record, catalog_record
                        )
                        marc = marc_bytes_of(record)
                        if old_marc != marc:
                            buffer.add(record_base, system_number, marc)

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


def _settle_window(
    ctx: ManagedTask,
    settle: Sequence[tuple[str, dict[str, tuple[str, list[dict]]], str]],
    window_links: dict[str, str],
) -> None:
    """Snapshot, outdate and stamp a whole window at once.

    Every record's new results are read together here rather than one record
    at a time at the end of its own turn, which is what the post-pass hashing
    used to cost. Deferring is safe because nothing in the loop reads back
    what this writes — the pass is finished with a record by the time it gets
    here.

    A record is stamped only when this pass actually found something, or when
    it has never been processed at all. Every reader of ``processed_at``
    treats it as a boolean — "has this been processed since it last changed" —
    so re-stamping a record whose links, comparisons and validations all still
    say what they said says nothing new. It is not free either: ``updated_at``
    is indexed and moves with any write, so each one of those rewrites the
    primary key, that index and the GIN index over ``search_vector``.
    """

    if not settle:
        return

    # The writes of this window have to be visible to the read below, and the
    # session does not autoflush.
    ctx.db_session.flush()
    new_hashes = _result_hashes_for(ctx.db_session, [record_id for record_id, _, _ in settle])

    for record_id, old_hashes, links_after in settle:
        results_changed = _apply_result_changes(
            ctx.db_session, record_id, old_hashes, new_hashes.get(record_id, {})
        )
        links_changed = links_after != window_links.get(record_id, "")

        catalog_record = ctx.db_session.get(CatalogRecord, record_id)
        if catalog_record is None:
            continue
        # Reaching here means the record was read, so whatever stopped the last
        # pass no longer does. Clearing it is also a change worth stamping for:
        # a record that was broken and produced nothing still has no results to
        # differ, so nothing else here would notice it had recovered.
        recovered = catalog_record.processing_error is not None
        if recovered:
            catalog_record.processing_error = None
        if results_changed or links_changed or recovered or catalog_record.processed_at is None:
            catalog_record.processed_at = config.timestamp
            catalog_record.save(ctx.db_session, commit=False)


#: Room for a pydantic error naming a few fields, and a hard stop well short of
#: a message that would make the row awkward to read or to index.
_PROCESSING_ERROR_LIMIT = 500


def _remember_processing_error(ctx: ManagedTask, record_id: str, reason: str) -> None:
    """Write on the record why this pass could not read it.

    Committed on its own rather than left to the window's commit. A later
    record in the same window can fail in a way that rolls the session back,
    and losing the explanation for record A because record B failed afterwards
    is exactly the silence this is here to end. Broken records are rare, so the
    extra write costs nothing at the scale that matters.
    """

    catalog_record = ctx.db_session.get(CatalogRecord, record_id)
    if catalog_record is None:
        return

    catalog_record.processing_error = reason[:_PROCESSING_ERROR_LIMIT]
    ctx.db_session.commit()


async def process_records(task_id: str) -> None:
    """
    Process catalog records: link to authorities, compare with linked records,
    validate, and mark as processed.
    """
    async with ManagedTask(task_id=task_id, lock_key=f"task-run-{task_id}") as ctx:
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
        confident_threshold = load_confident_threshold(ctx.db_session)

        comparator = load_comparator(ctx.db_session)
        if not comparator:
            ctx.logger.error("Comparator could not be initialized")
            return
        # Whether a linker's own verdict is the one this comparator would
        # reach; it is not when the comparison feature calls an LLM, which a
        # per-candidate gate cannot.
        _gate, gate_is_pipeline = load_gate_comparator(ctx.db_session)

        validator_instances = load_validators(ctx.db_session, settings.validators, ctx.logger)
        if not validator_instances:
            ctx.logger.error("Validators could not be initialized")
            return

        counters: defaultdict[LinkActionResult, int] = defaultdict(int)

        # Authority records land here rather than each rewriting its own
        # sector: one record written alone costs the whole sector, and a pass
        # writes one per link it finds.
        sectors = SectorBuffer(lambda: ctx.db_session)
        ctx.before_commit = sectors.flush_all

        record_ids = [
            r.id
            for r in build_filtered_query(ctx.db_session, filters)
            .with_entities(CatalogRecord.id)
            .all()
        ]
        ctx.total = len(record_ids)

        # Records are still fetched one at a time from whichever session is
        # live right now: handle_batch_progress_snippet cycles the session
        # every commit_interval records, and an ORM instance preloaded in bulk
        # beforehand is detached the moment that happens. The window carries
        # only parsed MARC, which belongs to no session and survives the cycle.
        for window in windows(record_ids, LINK_PREFETCH_WINDOW):
            window_marc = await announce_link_window(
                ctx.db_session, window, settings.target_bases, authority_linkers, ctx.logger
            )
            # What each record's results look like before it is reprocessed,
            # read for the window rather than once per record.
            window_hashes = _result_hashes_for(ctx.db_session, window)
            # Validators read the same records straight after the linkers do,
            # and answer the window from one query for the same reason.
            await announce_window(
                validator_instances,
                list(window_marc.values()),
                ctx.logger,
                lambda instance: instance.type.value,
            )

            CatalogRecord.warm(ctx.db_session, window)
            stored_marc = prefetch_linked_authority_marc(
                ctx.db_session, window, settings.target_bases
            )
            # What each record's links looked like before this pass, for the
            # same reason the result hashes are read: to tell afterwards
            # whether the pass found anything.
            window_links = _link_fingerprints_for(ctx.db_session, window)
            settle: list[tuple[str, dict[str, tuple[str, list[dict]]], str]] = []
            # What each validator already stored for these records, so that a
            # validator finding nothing new costs no query to discover it.
            stored_validations = stored_results_for(ctx.db_session, window)

            for record_id in window:
                catalog_record = ctx.db_session.get(CatalogRecord, record_id)
                if catalog_record is None:
                    # Deleted between building the id list and getting here.
                    handle_batch_progress_snippet(ctx)
                    continue

                try:
                    # Captured before reprocessing, from the window's read.
                    old_hashes = _old_hashes_for(ctx.db_session, record_id, window_hashes)

                    marc_record = window_marc.get(record_id) or catalog_record.get_record(
                        ctx.db_session
                    )

                    # A linker that ranked candidates already compared the
                    # pair it chose, which is the pair compared again below.
                    measured: dict[str, RecordComparisonResult] = {}
                    for target_base in settings.target_bases:
                        if target_base == catalog_record.base:
                            continue
                        found_link, linker_instance = await find_best_link_for_record(
                            catalog_record,
                            authority_linkers,
                            target_base,
                            marc_record,
                            ctx.logger,
                            confident_threshold,
                        )
                        if gate_is_pipeline and found_link and found_link.comparison:
                            measured[target_base] = found_link.comparison
                        results = handle_catalog_record_link_action(
                            ctx.db_session,
                            catalog_record,
                            found_link,
                            linker_instance,
                            target_base,
                            sectors,
                            stored_marc,
                        )
                        for result in results:
                            counters[result] += 1

                    # The links this record now has, with the authority records
                    # behind them, in one query. Both relationships load lazily,
                    # so refreshing the row and then walking them cost a SELECT
                    # for the record, one for its links, and one per link — 10%
                    # of the worker between them. The flush makes a link this
                    # pass deleted visible, which the row refresh did not do
                    # either: the session does not autoflush.
                    ctx.db_session.flush()
                    authority_links = (
                        ctx.db_session.query(AuthorityLink)
                        .options(joinedload(AuthorityLink.authority_record))
                        .filter_by(main_record_id=catalog_record.id)
                        .all()
                    )

                    # A comparison with nothing measured for it reads the
                    # authority record back, and one still waiting in the
                    # buffer reads as absent or as its previous self.
                    if any(
                        authority_link.base not in measured
                        and sectors.holds(
                            authority_link.authority_record.base,
                            authority_link.authority_record.system_number,
                        )
                        for authority_link in authority_links
                    ):
                        sectors.flush_all()

                    for authority_link in authority_links:
                        await handle_catalog_record_comparison(
                            ctx.db_session,
                            comparator,
                            ctx.logger,
                            authority_link.base,
                            catalog_record,
                            # Present only for a link this pass just made, so a
                            # link left standing from an earlier run is still
                            # compared against what is stored now.
                            precomputed=measured.get(authority_link.base),
                            record=marc_record,
                            link=authority_link,
                        )

                    for validator_instance in validator_instances:
                        await handle_catalog_record_validation(
                            ctx.db_session,
                            catalog_record,
                            validator_instance,
                            record=marc_record,
                            existing=stored_validations.get(
                                (record_id, validator_instance.type.value), []
                            ),
                        )

                    # Settled once for the whole window, below: what this
                    # record's results now say is two queries shared with
                    # every other record in it rather than two of its own.
                    settle.append((record_id, old_hashes, _link_fingerprint(authority_links)))

                    handle_batch_progress_snippet(ctx)

                # Both handlers report `record_id`, never catalog_record.id: reading
                # the instance here can raise a second error that buries the first.
                except AuthorityLinkingFailed as e:
                    # The record is readable; a lookup it depends on did not
                    # complete. Marking it broken would blame the record for
                    # someone else's outage, and the next pass would then
                    # "recover" it the moment the service came back, which says
                    # nothing about the record at all.
                    ctx.logger.error(f"Linking failed for record {record_id}: {e}")
                    counters[LinkActionResult.LinkingFailed] += 1
                    handle_batch_progress_snippet(ctx)

                except ValueError as e:
                    ctx.logger.warning(f"Skipping record {record_id}: {e}")
                    _remember_processing_error(ctx, record_id, str(e))
                    handle_batch_progress_snippet(ctx)

                except Exception as e:
                    ctx.db_session.rollback()
                    ctx.logger.error(f"Failed processing record {record_id}:\n{e}")
                    _remember_processing_error(ctx, record_id, f"{type(e).__name__}: {e}")
                    handle_batch_progress_snippet(ctx)

            _settle_window(ctx, settle, window_links)

        handle_final_batch_snippet(ctx)
        ctx.logger.info(f"Finished processing records, total records processed: {ctx.progress}")
        ctx.logger.info(
            "Summary of link actions: %s",
            {k.value: v for k, v in counters.items()},
        )

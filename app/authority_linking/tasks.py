import logging
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from marc_comparator.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
    BaseAuthorityLinker,
    LinkRequest,
)
from marc_comparator.authority_linkers import AuthorityLink as SdkAuthorityLink
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.marc_sectors import SectorBuffer, marc_bytes_of, upsert_record_in_sector
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from catalog_records.search import build_filtered_query
from config import config
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.settings import Settings, SettingsScope

from .models import AuthorityLinkingSettings, AuthorityLinkingTaskData


class LinkActionResult(StrEnum):
    NoLinkFound = "NoLinkFound"
    DeletedLink = "DeletedLink"
    UpdatedLink = "UpdatedLink"
    ReplacedLink = "ReplacedLink"
    CreatedLink = "CreatedLink"
    CreatedAuthorityRecord = "CreatedAuthorityRecord"
    UpdatedAuthorityRecord = "UpdatedAuthorityRecord"


@dataclass
class AuthorityLinkerInstance:
    linker: AuthorityLinker
    instance: BaseAuthorityLinker


class AuthorityLinkingFailed(RuntimeError):
    """No linker produced a result and at least one of them failed."""


#: Confidence at which the first stage stops looking. Matches the bottom of the
#: comparator's "Excellent" band, which is what scoring linkers report against.
DEFAULT_CONFIDENT_THRESHOLD = 0.9


def _confidence_of(link: SdkAuthorityLink) -> float:
    """A linker that reports no confidence is treated as the least certain.

    Confidences are not comparable across linkers in general: one may measure a
    match while another asserts a constant for every hit. Ranking them is only
    meaningful as a tie-break of last resort, which is all the second stage
    uses it for.
    """

    return link.confidence if link.confidence is not None else 0.0


#: Records announced to the linkers in one go.
#:
#: A linker that asks a remote service per record is what a full pass spends
#: most of its time on, and announcing a window lets it collapse those into a
#: few requests. Sized against both ends: large enough that the per-record cost
#: is the batched one, small enough that the parsed MARC held for a window is a
#: few megabytes rather than the whole run.
LINK_PREFETCH_WINDOW = 200


def windows(items: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def announce_link_window(
    db_session: DatabaseSession,
    record_ids: Sequence[str],
    target_bases: Sequence[str],
    linkers: list[AuthorityLinkerInstance],
    logger: logging.Logger,
) -> dict[str, MarcRecord]:
    """Tell every linker what is about to be asked, and keep the MARC read.

    Reading a window costs one parse per record, which the caller pays anyway
    when it reaches that record, so the records are handed back rather than
    dropped and read a second time.
    """

    marc_by_id: dict[str, MarcRecord] = {}
    requests: list[LinkRequest] = []

    for record_id in record_ids:
        catalog_record = db_session.get(CatalogRecord, record_id)
        if catalog_record is None:
            continue
        try:
            marc_record = catalog_record.get_record(db_session)
        except ValueError:
            # The caller reports this when it reaches the record. A window is a
            # hint, and must not turn one record's problem into the batch's.
            continue

        marc_by_id[record_id] = marc_record
        for target_base in target_bases:
            if target_base == catalog_record.base:
                continue
            requests.append(
                LinkRequest(
                    base=catalog_record.base,
                    system_number=catalog_record.system_number,
                    record=marc_record,
                    target_base=target_base,
                )
            )

    await announce_window(linkers, requests, logger, lambda linker: linker.linker.value)

    return marc_by_id


async def announce_window(
    plugins: Sequence[Any],
    announcement: Sequence[Any],
    logger: logging.Logger,
    name_of: Callable[[Any], str],
) -> None:
    """Warm each plugin's window, and let one that cannot warm its own pass.

    A prefetch is an optimisation: a plugin that fails here still answers
    record by record, which is slower rather than wrong, and not worth losing
    a batch over.
    """

    for plugin in plugins:
        try:
            await plugin.instance.prefetch(announcement)
        except Exception as e:
            logger.warning("Prefetch failed for %s: %s", name_of(plugin), e)


def load_authority_linkers(
    db_session: DatabaseSession,
    linkers: list[AuthorityLinker],
) -> list[AuthorityLinkerInstance] | None:
    """Load settings from DB and initialize linkers. Returns None on failure."""
    settings = Settings.get(db_session, SettingsScope.AuthorityLinking, AuthorityLinkingSettings)
    if not settings:
        return None
    result = init_authority_linkers(settings, linkers)
    from comparison.tasks import load_gate_comparator
    from harvest.storage import bind_plugin_storage

    # Ranking candidates on the configured scale rather than on whatever the
    # comparator class defaults to: otherwise a linker's minimum_confidence
    # means something other than the score an operator is shown.
    gate_comparator, _ = load_gate_comparator(db_session)
    for linker in result:
        bind_plugin_storage(
            linker.linker.value, linker.instance, db_session, logging.getLogger(__name__)
        )
        if gate_comparator is not None:
            linker.instance.bind_comparator(gate_comparator)
    return result or None


def load_confident_threshold(db_session: DatabaseSession) -> float:
    """The configured first-stage bar, or the default when nothing is stored."""

    settings = Settings.get(db_session, SettingsScope.AuthorityLinking, AuthorityLinkingSettings)
    return settings.confident_threshold if settings else DEFAULT_CONFIDENT_THRESHOLD


def init_authority_linkers(
    settings: AuthorityLinkingSettings,
    linkers: list[AuthorityLinker],
) -> list[AuthorityLinkerInstance]:
    """
    Initialize authority linkers from validated settings.
    Expects settings to be valid; skips linkers with missing class.
    """
    authority_linkers: list[AuthorityLinkerInstance] = []
    for linker in linkers:
        linker_cls = AUTHORITY_LINKER_DISPATCHER.get(linker)
        if not linker_cls:
            continue

        config_model = linker_cls.config_model
        if config_model is None:
            linker_instance = linker_cls()
        else:
            # Settings may store null for a configured linker; fall back to the
            # config model's own defaults rather than constructing without one.
            stored = getattr(settings, linker.value.replace("-", "_"), None)
            linker_instance = linker_cls(
                config_model.model_validate(stored) if stored is not None else config_model()
            )

        authority_linkers.append(AuthorityLinkerInstance(linker, linker_instance))

    return authority_linkers


async def find_best_link_for_record(
    catalog_record: CatalogRecord,
    authority_linkers: list[AuthorityLinkerInstance],
    target_base: str,
    marc_record: MarcRecord,
    logger: logging.Logger,
    confident_threshold: float = DEFAULT_CONFIDENT_THRESHOLD,
) -> tuple[SdkAuthorityLink | None, AuthorityLinkerInstance | None]:
    """
    Link a record in two stages.

    The first stage stops at the first linker confident enough to decide, in the
    order they are configured, so the rest are never asked. Only when no linker
    is confident does the second stage weigh every proposal and keep the best
    one — worth the extra work exactly because it is rare.

    A linker that reports a link is trusted about its own floor: its confidence
    is what it measured, and nothing here re-judges it beyond ranking.

    Raises ``AuthorityLinkingFailed`` when nothing was found and a linker
    failed. The caller treats "no link" as evidence that an existing link is
    obsolete and deletes it, so a lookup that never completed must not be
    reported as an empty result.
    """
    candidates: list[tuple[SdkAuthorityLink, AuthorityLinkerInstance]] = []
    failures: list[Exception] = []

    for authority_linker in authority_linkers:
        try:
            link = await authority_linker.instance.run(
                catalog_record.base,
                catalog_record.system_number,
                marc_record,
                target_base,
            )
        except Exception as e:
            failures.append(e)
            logger.error(
                f"Failed linking with {authority_linker.linker.value} "
                f"for record {catalog_record.id}: {e}"
            )
            continue

        if link is None:
            continue
        candidates.append((link, authority_linker))
        if _confidence_of(link) >= confident_threshold:
            # Confident and first in configured order: asking the remaining
            # linkers could only produce a rival to the same answer.
            return link, authority_linker

    if not candidates:
        if failures:
            raise AuthorityLinkingFailed(
                f"Every linker failed for record {catalog_record.id}"
            ) from failures[0]
        return None, None

    best_link, best_linker = max(candidates, key=lambda item: _confidence_of(item[0]))
    logger.info(
        "No confident link for record %s; keeping the best of %d proposals (%s, confidence %.2f)",
        catalog_record.id,
        len(candidates),
        best_linker.linker.value,
        _confidence_of(best_link),
    )
    return best_link, best_linker


def get_existing_link(
    db_session: DatabaseSession,
    main_record_id: str,
    base: str,
) -> AuthorityLink | None:
    """Return the single authority link for this record and base, if any."""
    return AuthorityLink.find_by_main_record_and_base(db_session, main_record_id, base)


def scenario_no_link_no_existing() -> list[LinkActionResult]:
    """No link found and no existing links."""
    return [LinkActionResult.NoLinkFound]


def scenario_no_link_with_existing(
    db_session: DatabaseSession,
    existing_link: AuthorityLink,
) -> list[LinkActionResult]:
    """No link found but an existing link exists; delete it."""
    existing_link.delete(db_session, commit=False)
    return [LinkActionResult.DeletedLink]


def store_authority_marc(
    db_session: DatabaseSession,
    base: str,
    system_number: str,
    marc: bytes,
    sectors: SectorBuffer | None,
) -> None:
    """Put an authority record's MARC where the rest of the system reads it.

    Written on its own, one record costs a whole sector: decompressed, merged,
    recompressed and re-indexed, with every record it shares the sector with
    dropped from the cache. That was measured at 189 ms a time and was the
    largest thing a processing pass did.

    Given a buffer the record waits there until its sector is written once for
    everything that landed in it. The caller owns the flushing, and owes the
    buffer a flush before anything reads the record back.
    """

    if sectors is None:
        upsert_record_in_sector(db_session, base, system_number, marc)
        return
    sectors.add(base, system_number, marc)


def scenario_found_link_update(
    db_session: DatabaseSession,
    found_link: SdkAuthorityLink,
    linker_instance: AuthorityLinkerInstance,
    current_link: AuthorityLink,
    sectors: SectorBuffer | None = None,
) -> list[LinkActionResult]:
    """Found link matches existing link; update in place."""
    current_link.confidence = found_link.confidence
    authority_record = current_link.authority_record
    authority_record.latest_sync = config.timestamp
    authority_record.source_name = linker_instance.linker.value
    authority_record.update_search_text_from(found_link.record)

    store_authority_marc(
        db_session,
        authority_record.base,
        authority_record.system_number,
        marc_bytes_of(found_link.record),
        sectors,
    )

    current_link.save(db_session, commit=False)
    return [
        LinkActionResult.UpdatedLink,
        LinkActionResult.UpdatedAuthorityRecord,
    ]


def _upsert_authority_record_and_link(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_instance: AuthorityLinkerInstance,
    target_base: str,
    sectors: SectorBuffer | None = None,
) -> tuple[CatalogRecord, LinkActionResult]:
    """Upsert the authority CatalogRecord, store its MARC, and create a new link."""
    authority_record = CatalogRecord.find_by_base_and_system_number(
        db_session, found_link.base, found_link.system_number
    )

    if not authority_record:
        authority_record = CatalogRecord(
            base=found_link.base,
            system_number=found_link.system_number,
            source_type=CatalogRecordSource.AuthorityLinker,
            source_name=linker_instance.linker.value,
        )
        record_result = LinkActionResult.CreatedAuthorityRecord
    else:
        authority_record.latest_sync = config.timestamp
        authority_record.source_name = linker_instance.linker.value
        record_result = LinkActionResult.UpdatedAuthorityRecord

    authority_record.update_search_text_from(found_link.record)
    authority_record.save(db_session, commit=False)
    store_authority_marc(
        db_session,
        found_link.base,
        found_link.system_number,
        marc_bytes_of(found_link.record),
        sectors,
    )

    new_link = AuthorityLink(
        main_record_id=catalog_record.id,
        linker=linker_instance.linker.value,
        base=target_base,
        authority_record_id=authority_record.id,
        confidence=found_link.confidence,
    )
    new_link.save(db_session, commit=False)
    return authority_record, record_result


def scenario_found_link_replace(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_instance: AuthorityLinkerInstance,
    existing_link: AuthorityLink,
    target_base: str,
    sectors: SectorBuffer | None = None,
) -> list[LinkActionResult]:
    """Found link has different authority than existing; replace."""
    existing_link.delete(db_session, commit=False)
    _, record_result = _upsert_authority_record_and_link(
        db_session, catalog_record, found_link, linker_instance, target_base, sectors
    )
    return [LinkActionResult.ReplacedLink, record_result]


def scenario_found_link_create(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_instance: AuthorityLinkerInstance,
    target_base: str,
    sectors: SectorBuffer | None = None,
) -> list[LinkActionResult]:
    """Found new link; create it (no existing link for this base)."""
    _, record_result = _upsert_authority_record_and_link(
        db_session, catalog_record, found_link, linker_instance, target_base, sectors
    )
    return [LinkActionResult.CreatedLink, record_result]


def handle_catalog_record_link_action(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink | None,
    linker_instance: AuthorityLinkerInstance | None,
    target_base: str,
    sectors: SectorBuffer | None = None,
) -> list[LinkActionResult]:
    """
    Get existing link, determine scenario, and run the appropriate handler.
    At most one link per record+base. Returns LinkActionResult list.
    """
    existing_link = get_existing_link(db_session, catalog_record.id, target_base)

    # find_best_link_for_record yields the link and its linker together or
    # neither, so one being None means there is no found link at all.
    if found_link is None or linker_instance is None:
        if existing_link is None:
            return scenario_no_link_no_existing()
        return scenario_no_link_with_existing(db_session, existing_link)

    if existing_link is None:
        return scenario_found_link_create(
            db_session,
            catalog_record,
            found_link,
            linker_instance,
            target_base,
            sectors,
        )

    if existing_link.system_number == found_link.system_number:
        return scenario_found_link_update(
            db_session, found_link, linker_instance, existing_link, sectors
        )

    return scenario_found_link_replace(
        db_session,
        catalog_record,
        found_link,
        linker_instance,
        existing_link,
        target_base,
        sectors,
    )


async def authority_linking(task_id: str) -> None:
    async with ManagedTask(task_id=task_id, lock_key=f"task-run-{task_id}") as ctx:
        data = AuthorityLinkingTaskData.model_validate(ctx.task.data)

        authority_linkers = load_authority_linkers(ctx.db_session, data.linkers)
        if not authority_linkers:
            ctx.logger.error("Authority linkers could not be initialized")
            return
        confident_threshold = load_confident_threshold(ctx.db_session)

        counters: defaultdict[LinkActionResult, int] = defaultdict(int)

        # One record written on its own costs the whole sector it lives in,
        # and this task writes one per link it finds.
        sectors = SectorBuffer(lambda: ctx.db_session)
        ctx.before_commit = sectors.flush_all

        record_ids = [
            r.id
            for r in build_filtered_query(ctx.db_session, data.filters)
            .with_entities(CatalogRecord.id)
            .all()
        ]
        ctx.total = len(record_ids)

        for window in windows(record_ids, LINK_PREFETCH_WINDOW):
            window_marc = await announce_link_window(
                ctx.db_session, window, [data.target_base], authority_linkers, ctx.logger
            )

            for record_id in window:
                catalog_record = ctx.db_session.get(CatalogRecord, record_id)
                if catalog_record is None:
                    # Deleted between building the id list and getting here.
                    handle_batch_progress_snippet(ctx)
                    continue

                try:
                    if catalog_record.base == data.target_base:
                        handle_batch_progress_snippet(ctx)
                        continue

                    marc_record = window_marc.get(record_id) or catalog_record.get_record(
                        ctx.db_session
                    )

                    found_link, linker_instance = await find_best_link_for_record(
                        catalog_record,
                        authority_linkers,
                        data.target_base,
                        marc_record,
                        ctx.logger,
                        confident_threshold,
                    )

                    results = handle_catalog_record_link_action(
                        ctx.db_session,
                        catalog_record,
                        found_link,
                        linker_instance,
                        data.target_base,
                        sectors,
                    )

                    for result in results:
                        counters[result] += 1

                    handle_batch_progress_snippet(ctx)

                except ValueError as e:
                    ctx.logger.warning(f"Skipping record {catalog_record.id}: {e}")
                    handle_batch_progress_snippet(ctx)

                except Exception as e:
                    ctx.db_session.rollback()
                    ctx.logger.error(f"Failed linking record {catalog_record.id}:\n{e}")
                    handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(f"Finished authority linking, total records processed: {ctx.progress}")
        ctx.logger.info(
            "Summary of link actions: %s",
            {result.value: count for result, count in counters.items()},
        )

import logging
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import List, Optional, Tuple

from marc_comparator.authority_linkers import AUTHORITY_LINKER_DISPATCHER
from marc_comparator.authority_linkers import AuthorityLink as SdkAuthorityLink
from marc_comparator.authority_linkers import (
    AuthorityLinker,
    BaseAuthorityLinker,
)
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.tasks import ManagedTask
from catalog_records.tasks import (
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
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


def init_authority_linkers(
    settings: AuthorityLinkingSettings,
    linkers: List[AuthorityLinker],
) -> List[AuthorityLinkerInstance]:
    """
    Initialize authority linkers from validated settings.
    Expects settings to be valid; skips linkers with missing class.
    """
    authority_linkers: List[AuthorityLinkerInstance] = []
    for linker in linkers:
        linker_cls = AUTHORITY_LINKER_DISPATCHER.get(linker)
        if not linker_cls:
            continue

        linker_config = (
            getattr(settings, linker.value.replace("-", "_"), None)
            if linker_cls.config_model
            else None
        )

        linker_instance = (
            linker_cls(
                config=linker_cls.config_model.model_validate(linker_config)
            )
            if linker_config
            else linker_cls()
        )

        authority_linkers.append(
            AuthorityLinkerInstance(linker, linker_instance)
        )

    return authority_linkers


async def find_best_link_for_record(
    catalog_record: CatalogRecord,
    authority_linkers: List[AuthorityLinkerInstance],
    target_base: str,
    marc_record: MarcRecord,
    logger: logging.Logger,
) -> Tuple[SdkAuthorityLink | None, AuthorityLinkerInstance | None]:
    """
    Run all linkers for a catalog record and return the link with highest
    confidence.
    """
    candidates: List[Tuple[SdkAuthorityLink, AuthorityLinkerInstance]] = []

    for authority_linker in authority_linkers:
        try:
            link = await authority_linker.instance.run(
                catalog_record.base,
                catalog_record.system_number,
                marc_record,
                target_base,
            )
            if link is not None:
                candidates.append((link, authority_linker))
        except Exception as e:
            logger.error(
                f"Failed linking with {authority_linker.linker.value} "
                f"for record {catalog_record.id}: {e}"
            )

    if not candidates:
        return None, None

    def confidence_key(
        item: Tuple[SdkAuthorityLink, AuthorityLinkerInstance],
    ) -> float:
        c = item[0].confidence
        return c if c is not None else 0.0

    best = max(candidates, key=confidence_key)
    return best[0], best[1]


def get_existing_link(
    db_session: DatabaseSession,
    main_record_id: str,
    base: str,
) -> Optional[AuthorityLink]:
    """Return the single authority link for this record and base, if any."""
    return AuthorityLink.find_by_main_record_and_base(
        db_session, main_record_id, base
    )


def scenario_no_link_no_existing() -> List[LinkActionResult]:
    """No link found and no existing links."""
    return [LinkActionResult.NoLinkFound]


def scenario_no_link_with_existing(
    db_session: DatabaseSession,
    existing_link: AuthorityLink,
) -> List[LinkActionResult]:
    """No link found but an existing link exists; delete it."""
    existing_link.delete(db_session)
    return [LinkActionResult.DeletedLink]


def scenario_found_link_update(
    db_session: DatabaseSession,
    found_link: SdkAuthorityLink,
    linker_instance: AuthorityLinkerInstance,
    current_link: AuthorityLink,
) -> List[LinkActionResult]:
    """Found link matches existing link; update in place."""
    current_link.confidence = found_link.confidence
    current_link.authority_record.marc = found_link.record._marc
    current_link.authority_record.latest_sync = config.timestamp
    current_link.authority_record.source_name = linker_instance.linker.value

    current_link.save(db_session)
    return [
        LinkActionResult.UpdatedLink,
        LinkActionResult.UpdatedAuthorityRecord,
    ]


def scenario_found_link_replace(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_instance: AuthorityLinkerInstance,
    existing_link: AuthorityLink,
    target_base: str,
) -> List[LinkActionResult]:
    """Found link has different authority than existing; replace."""
    existing_link.delete(db_session)

    authority_record = CatalogRecord.find_by_base_and_system_number(
        db_session, found_link.base, found_link.system_number
    )

    results = [LinkActionResult.ReplacedLink]
    if not authority_record:
        authority_record = CatalogRecord(
            base=found_link.base,
            system_number=found_link.system_number,
            marc=found_link.record._marc,
            source_type=CatalogRecordSource.AuthorityLinker,
            source_name=linker_instance.linker.value,
        )
        results.append(LinkActionResult.CreatedAuthorityRecord)
    else:
        authority_record.marc = found_link.record._marc
        authority_record.latest_sync = config.timestamp
        authority_record.source_name = linker_instance.linker.value
        results.append(LinkActionResult.UpdatedAuthorityRecord)

    authority_record.save(db_session)

    new_link = AuthorityLink(
        main_record_id=catalog_record.id,
        linker=linker_instance.linker.value,
        base=target_base,
        authority_record_id=authority_record.id,
        confidence=found_link.confidence,
    )
    new_link.save(db_session)
    return results


def scenario_found_link_create(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_instance: AuthorityLinkerInstance,
    target_base: str,
) -> List[LinkActionResult]:
    """Found new link; create it (no existing link for this base)."""
    authority_record = CatalogRecord.find_by_base_and_system_number(
        db_session, found_link.base, found_link.system_number
    )

    results = [LinkActionResult.CreatedLink]
    if not authority_record:
        authority_record = CatalogRecord(
            base=found_link.base,
            system_number=found_link.system_number,
            marc=found_link.record._marc,
            source_type=CatalogRecordSource.AuthorityLinker,
            source_name=linker_instance.linker.value,
        )
        results.append(LinkActionResult.CreatedAuthorityRecord)
    else:
        authority_record.marc = found_link.record._marc
        authority_record.latest_sync = config.timestamp
        authority_record.source_name = linker_instance.linker.value
        results.append(LinkActionResult.UpdatedAuthorityRecord)

    authority_record.save(db_session)

    new_link = AuthorityLink(
        main_record_id=catalog_record.id,
        linker=linker_instance.linker.value,
        base=target_base,
        authority_record_id=authority_record.id,
        confidence=found_link.confidence,
    )
    new_link.save(db_session)
    return results


def handle_catalog_record_link_action(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink | None,
    linker_instance: AuthorityLinkerInstance | None,
    target_base: str,
) -> List[LinkActionResult]:
    """
    Get existing link, determine scenario, and run the appropriate handler.
    At most one link per record+base. Returns LinkActionResult list.
    """
    existing_link = get_existing_link(
        db_session, catalog_record.id, target_base
    )

    if found_link is None and existing_link is None:
        return scenario_no_link_no_existing()

    if found_link is None and existing_link is not None:
        return scenario_no_link_with_existing(db_session, existing_link)

    if (
        found_link is not None
        and existing_link is not None
        and existing_link.system_number == found_link.system_number
    ):
        return scenario_found_link_update(
            db_session, found_link, linker_instance, existing_link
        )

    if (
        found_link is not None
        and existing_link is not None
        and existing_link.system_number != found_link.system_number
    ):
        return scenario_found_link_replace(
            db_session,
            catalog_record,
            found_link,
            linker_instance,
            existing_link,
            target_base,
        )

    return scenario_found_link_create(
        db_session,
        catalog_record,
        found_link,
        linker_instance,
        target_base,
    )


async def authority_linking(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = AuthorityLinkingTaskData.model_validate(ctx.task.data)
        settings = Settings.get(
            ctx.db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings,
        )

        if not settings:
            ctx.logger.error("Authority linking settings not found")
            return

        authority_linkers = init_authority_linkers(settings, data.linkers)

        if not authority_linkers:
            ctx.logger.error("No authority linkers could be initialized")
            return

        counters: defaultdict[LinkActionResult, int] = defaultdict(int)

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
            try:
                marc_record = MarcRecord.from_mrc(catalog_record.marc)

                found_link, linker_instance = await find_best_link_for_record(
                    catalog_record,
                    authority_linkers,
                    data.target_base,
                    marc_record,
                    ctx.logger,
                )

                results = handle_catalog_record_link_action(
                    ctx.db_session,
                    catalog_record,
                    found_link,
                    linker_instance,
                    data.target_base,
                )

                for result in results:
                    counters[result] += 1

                await handle_batch_progress_snippet(ctx, catalog_record)

            except Exception as e:
                ctx.logger.error(
                    f"Failed linking record {catalog_record.id}:\n{e}"
                )

        await handle_final_batch_snippet(ctx)

        ctx.logger.info(
            "Finished authority linking, "
            f"total records processed: {ctx.progress}"
        )
        ctx.logger.info(
            "Summary of link actions: %s",
            {result.value: count for result, count in counters.items()},
        )

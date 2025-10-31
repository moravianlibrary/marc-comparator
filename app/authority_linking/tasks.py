from dataclasses import dataclass
from typing import List

from marc_comparator_sdk.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
    BaseAuthorityLinker,
)
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.tasks import ManagedTask
from config import config
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.settings import Settings, SettingsScope

from .models import AuthorityLinkingSettings, AuthorityLinkingTaskData


@dataclass
class AuthorityLinkerInstance:
    linker: AuthorityLinker
    instance: BaseAuthorityLinker


async def _link_record_with_linker(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    authority_linker: AuthorityLinkerInstance,
    target_base: str,
) -> bool:
    link = await authority_linker.instance.run(
        catalog_record.base,
        catalog_record.system_number,
        MarcRecord.from_mrc(catalog_record.marc),
        target_base,
    )

    if link is None:
        return False

    current_link = AuthorityLink.find(
        db_session,
        catalog_record.id,
        CatalogRecord.generate_id(link.base, link.system_number),
    )

    if current_link is None:
        authority_record = CatalogRecord.find_by_base_and_system_number(
            db_session, link.base, link.system_number
        )

        if not authority_record:
            authority_record = CatalogRecord(
                base=link.base,
                system_number=link.system_number,
                marc=link.record._marc,
                source_type=CatalogRecordSource.AuthorityLinker,
                source_name=authority_linker.linker.value,
            )
        else:
            authority_record.marc = link.record._marc
            authority_record.last_sync = config.timestamp
            authority_record.source_name = authority_linker.linker.value
        authority_record.save(db_session)

        current_link = AuthorityLink(
            main_record_id=catalog_record.id,
            authority_record_id=authority_record.id,
            confidence=link.confidence,
        )
    else:
        current_link.confidence = link.confidence
        current_link.authority_record.marc = link.record._marc
        current_link.authority_record.last_sync = config.timestamp
        current_link.authority_record.source_name = (
            authority_linker.linker.value
        )

    current_link.save(db_session)
    await current_link.main_record.index()


async def authority_linking(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = AuthorityLinkingTaskData.model_validate(ctx.task.data)
        settings = Settings.get(
            ctx.db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings,
        )

        if not settings:
            raise ValueError("Authority linking settings not found")

        authority_linkers: List[AuthorityLinkerInstance] = []
        for linker in data.linkers:
            linker_cls = AUTHORITY_LINKER_DISPATCHER.get(linker)
            if not linker_cls:
                continue

            linker_config = (
                getattr(settings, linker.value.replace("-", "_"), None)
                if linker_cls.config_model
                else None
            )

            linker_instance = (
                linker_cls(config=linker_cls.model_validate(linker_config))
                if linker_config
                else linker_cls()
            )

            authority_linkers.append(
                AuthorityLinkerInstance(linker, linker_instance)
            )

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
            for authority_linker in authority_linkers:
                if await _link_record_with_linker(
                    ctx.db_session,
                    catalog_record,
                    authority_linker,
                    data.target_base,
                ):
                    break  # Stop after the first successful linking

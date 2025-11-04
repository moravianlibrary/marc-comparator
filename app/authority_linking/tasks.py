from dataclasses import dataclass
from typing import List

from marc_comparator.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
    BaseAuthorityLinker,
)
from marcdantic import MarcRecord

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


@dataclass
class AuthorityLinkerInstance:
    linker: AuthorityLinker
    instance: BaseAuthorityLinker


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

        authority_linkers: List[AuthorityLinkerInstance] = []
        for linker in data.linkers:
            try:
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
                        config=linker_cls.config_model.model_validate(
                            linker_config
                        )
                    )
                    if linker_config
                    else linker_cls()
                )

                authority_linkers.append(
                    AuthorityLinkerInstance(linker, linker_instance)
                )

            except Exception as e:
                ctx.logger.error(
                    f"Error initializing authority linker '{linker}':\n{e}"
                )

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
            for authority_linker in authority_linkers:
                try:
                    link = await authority_linker.instance.run(
                        catalog_record.base,
                        catalog_record.system_number,
                        MarcRecord.from_mrc(catalog_record.marc),
                        data.target_base,
                    )

                    if link is None:
                        ctx.logger.info(
                            f"No authority link found for {catalog_record.id} "
                            f"to base {data.target_base} "
                            f"using linker {authority_linker.linker.value}"
                        )
                        continue

                    current_link = AuthorityLink.find_by_linker_and_base(
                        ctx.db_session,
                        catalog_record.id,
                        authority_linker.linker.value,
                        data.target_base,
                    )

                    if (
                        current_link is not None
                        and current_link.system_number == link.system_number
                    ):
                        ctx.logger.info(
                            f"Updating existing authority link for "
                            f"record {catalog_record.id} "
                            f"to base {data.target_base} "
                            f"using linker {authority_linker.linker.value}"
                        )

                        current_link.confidence = link.confidence
                        current_link.authority_record.marc = link.record._marc
                        current_link.authority_record.last_sync = (
                            config.timestamp
                        )
                        current_link.authority_record.source_name = (
                            authority_linker.linker.value
                        )

                        current_link.save(ctx.db_session)

                        await handle_batch_progress_snippet(
                            ctx, catalog_record
                        )

                        break  # Pair using first found link only

                    elif (
                        current_link is not None
                        and current_link.system_number != link.system_number
                    ):
                        ctx.logger.info(
                            f"Conflict detected for authority link for "
                            f"record {catalog_record.id} "
                            f"to base {data.target_base} "
                            f"using linker {authority_linker.linker.value}. "
                            f"Existing system number "
                            f"{current_link.system_number} differs from "
                            f"newly found {link.system_number}. Deleting."
                        )
                        current_link.delete(ctx.db_session)

                    authority_record = (
                        CatalogRecord.find_by_base_and_system_number(
                            ctx.db_session, link.base, link.system_number
                        )
                    )

                    if not authority_record:
                        ctx.logger.info(
                            f"Creating new authority record for "
                            f"link {link.base}-{link.system_number} "
                            f"using linker {authority_linker.linker.value}"
                        )

                        authority_record = CatalogRecord(
                            base=link.base,
                            system_number=link.system_number,
                            marc=link.record._marc,
                            source_type=CatalogRecordSource.AuthorityLinker,
                            source_name=authority_linker.linker.value,
                        )
                    else:
                        ctx.logger.info(
                            f"Updating existing authority record for "
                            f"link {link.base}-{link.system_number} "
                            f"using linker {authority_linker.linker.value}"
                        )

                        authority_record.marc = link.record._marc
                        authority_record.last_sync = config.timestamp
                        authority_record.source_name = (
                            authority_linker.linker.value
                        )

                    authority_record.save(ctx.db_session)

                    current_link = AuthorityLink(
                        main_record_id=catalog_record.id,
                        linker=authority_linker.linker.value,
                        base=data.target_base,
                        authority_record_id=authority_record.id,
                        confidence=link.confidence,
                    )
                    current_link.save(ctx.db_session)

                    await handle_batch_progress_snippet(ctx, catalog_record)

                    break  # Pair using first found link only

                except Exception as e:
                    ctx.logger.error(
                        f"Failed linking authority "
                        f"with linker {authority_linker.linker.value} "
                        f"for record {catalog_record.id}:\n{e}"
                    )

        await handle_final_batch_snippet(ctx)

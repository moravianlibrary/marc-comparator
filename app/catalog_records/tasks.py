from collections import defaultdict

from aleph_nought import RecordStatus
from marcdantic import MarcRecord

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.indexer import IndexerQuery
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from authority_linking.models import AuthorityLinkingSettings
from authority_linking.tasks import (
    LinkActionResult,
    find_best_link_for_record,
    handle_catalog_record_link_action,
    init_authority_linkers,
)
from catalog_records.models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    ProcessRecordsSettings,
    SetRecordsVisibilityData,
    SyncRecordsData,
)
from comparison.models import ComparisonSettings
from comparison.tasks import handle_catalog_record_comparison, init_comparator
from config import config
from entities.catalog_record import CatalogRecord
from entities.settings import Settings, SettingsScope
from validation.models import ValidationSettings
from validation.tasks import handle_catalog_record_validation, init_validators


class AlephError(Exception):
    pass


def save_record_snippet(
    ctx: ManagedTask,
    base: str,
    system_number: str,
    record: MarcRecord,
) -> CatalogRecord:
    catalog_record = CatalogRecord.find_by_base_and_system_number(
        ctx.db_session, base, system_number
    )

    if catalog_record:
        catalog_record.marc = record._marc
        catalog_record.deleted = False
        catalog_record.latest_sync = config.timestamp
    else:
        catalog_record = CatalogRecord(
            base=base, system_number=system_number, marc=record._marc
        )

    return catalog_record.save(ctx.db_session)


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
            ctx.logger.error(
                f"Record with system number '{system_number}' not found"
            )
            return

        await save_record_snippet(ctx, base, system_number, record).index()

        ctx.logger.info(f"Finished fetching record {base}-{system_number}")


async def fetch_batch_of_records_task(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = FetchBatchOfRecordsData.model_validate(ctx.task.data)

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
                        await handle_batch_progress_snippet(ctx)
                        continue

                    await handle_batch_progress_snippet(
                        ctx,
                        save_record_snippet(ctx, base, system_number, record),
                    )

                except Exception as e:
                    ctx.logger.error(
                        f"Failed processing record {system_number}:\n{e}"
                    )
                    await handle_batch_progress_snippet(ctx)

        await handle_final_batch_snippet(ctx)

        ctx.logger.info(
            "Finished fetching batch of records, "
            f"total records processed: {ctx.progress}"
        )


async def records_sync_task(
    task_id: str, lock_key: str, lock_blocking_timeout: int
):
    """
    Run a catalog synchronization task to update locally stored catalog records
    from an Aleph server defined by the given base and configuration.

    This task ensures that only one sync runs per catalog base at a time
    using a distributed lock.
    It processes records fetched from the external Aleph OAI client
    and updates the database accordingly.

    Parameters
    ----------
    task_id : str
        The ID of the Celery task instance (used for task context and ID).
    lock_key : str
        The key used for acquiring the distributed lock.
    lock_blocking_timeout : int
        The maximum time to wait for acquiring the lock.
    """
    async with ManagedTask(
        task_id=task_id,
        lock_key=lock_key,
        lock_blocking_timeout=lock_blocking_timeout,
    ) as ctx:
        data = SyncRecordsData.model_validate(ctx.task.data)

        base = data.base
        from_date = (
            data.from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            if data.from_date
            else None
        )

        if from_date is None:
            ctx.logger.info(f"Starting catalog sync for base '{base}'")
        else:
            ctx.logger.info(
                f"Starting catalog sync for base '{base}' "
                f"from date '{from_date}'"
            )

        client = AlephClientRegistry.get(base)
        if not client.OAI.is_available():
            ctx.logger.error(f"OAI service for {base} is not available")
            return

        for base, system_number, status, record in client.OAI.list_records(
            from_date, None
        ):
            try:
                if status == RecordStatus.Failed:
                    ctx.logger.error(
                        f"Failed fetching record {base}-{system_number}."
                    )
                    continue

                catalog_record = (
                    ctx.db_session.query(CatalogRecord)
                    .filter_by(base=base, system_number=system_number)
                    .first()
                )

                if status == RecordStatus.Deleted and catalog_record is None:
                    pass

                elif status == RecordStatus.Deleted and catalog_record:
                    catalog_record.latest_sync = config.timestamp
                    catalog_record.deleted = True
                    ctx.logger.info(
                        f"Marking record {base}-{system_number} as deleted."
                    )

                elif not record:
                    ctx.logger.error(
                        f"Record {base}-{system_number} has no MARC data."
                    )
                    catalog_record = None

                else:
                    catalog_record = save_record_snippet(
                        ctx, base, system_number, record
                    )

                await handle_batch_progress_snippet(ctx, catalog_record)

            except Exception as e:
                ctx.logger.error(
                    f"Failed processing record {system_number}:\n{e}"
                )
                await handle_batch_progress_snippet(ctx)

        await handle_final_batch_snippet(ctx)

        ctx.logger.info(
            f"Finished catalog sync, total records processed: {ctx.progress}"
        )


async def reindex_records(task_id: str):
    async with ManagedTask(task_id=task_id) as ctx:
        query = IndexerQuery.model_validate(ctx.task.data)

        ctx.logger.info("Starting reindexing of catalog records")

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, query
        ):
            await handle_batch_progress_snippet(ctx, catalog_record)

        await handle_final_batch_snippet(ctx)

        ctx.logger.info(
            f"Finished reindexing, total records processed: {ctx.progress}"
        )


async def set_records_visibility(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = SetRecordsVisibilityData.model_validate(ctx.task.data)
        query = data.query
        hide = data.visible is False

        if hide:
            ctx.logger.info("Setting records to hidden state")
        else:
            ctx.logger.info("Setting records to visible state")

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, query
        ):
            catalog_record.hidden = hide
            ctx.db_session.add(catalog_record)

            await handle_batch_progress_snippet(ctx, catalog_record)

        await handle_final_batch_snippet(ctx)

        ctx.logger.info(
            "Finished setting hidden state, "
            f"total records processed: {ctx.progress}"
        )


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

        query = IndexerQuery.model_validate(ctx.task.data)
        ctx.logger.info("Starting processing of catalog records")

        al_settings = Settings.get(
            ctx.db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings,
        )
        if not al_settings:
            ctx.logger.error("Authority linking settings not found")
            return

        authority_linkers = init_authority_linkers(
            al_settings, settings.authority_linkers
        )
        if not authority_linkers:
            ctx.logger.error("No authority linkers could be initialized")
            return

        c_settings = Settings.get(
            ctx.db_session,
            SettingsScope.Comparison,
            ComparisonSettings,
        )
        if not c_settings:
            ctx.logger.error("Comparison settings not found")
            return

        try:
            comparator = init_comparator(c_settings, settings.comparator)
        except ValueError as e:
            ctx.logger.error(str(e))
            return

        validation_settings = Settings.get(
            ctx.db_session,
            SettingsScope.Validation,
            ValidationSettings,
        )
        if not validation_settings:
            ctx.logger.error("Validation settings not found")
            return

        validator_instances = init_validators(
            validation_settings, settings.validators, ctx.logger
        )

        counters: defaultdict[LinkActionResult, int] = defaultdict(int)

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, query
        ):
            try:
                marc_record = MarcRecord.from_mrc(catalog_record.marc)

                for target_base in settings.target_bases:
                    found_link, linker_instance = (
                        await find_best_link_for_record(
                            catalog_record,
                            authority_linkers,
                            target_base,
                            marc_record,
                            ctx.logger,
                        )
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
                        settings.comparator.value,
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

                catalog_record.processed_at = config.timestamp
                catalog_record.save(ctx.db_session)

                await handle_batch_progress_snippet(ctx, catalog_record)

            except Exception as e:
                ctx.logger.error(
                    f"Failed processing record {catalog_record.id}:\n{e}"
                )

        await handle_final_batch_snippet(ctx)
        ctx.logger.info(
            "Finished processing records, "
            f"total records processed: {ctx.progress}"
        )
        ctx.logger.info(
            "Summary of link actions: %s",
            {k.value: v for k, v in counters.items()},
        )

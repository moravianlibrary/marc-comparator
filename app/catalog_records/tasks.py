from aleph_nought import RecordStatus
from marcdantic import MarcRecord

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.indexer import IndexerQuery
from adapters.tasks import ManagedTask
from catalog_records.models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    SetRecordsVisibilityData,
    SyncRecordsData,
)
from config import config
from entities.catalog_record import CatalogRecord


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


async def handle_batch_progress_snippet(
    ctx: ManagedTask, catalog_record: CatalogRecord | None = None
):
    ctx.progress += 1

    if ctx.progress % ctx.task_settings.progress_update_interval == 0:
        ctx.logger.info(f"Processed {ctx.progress} records so far.")

        ctx.task.progress = ctx.progress / ctx.total
        await ctx.update_progress()

    if catalog_record is None:
        return

    ctx.index_batch.append(catalog_record)

    if len(ctx.index_batch) % ctx.task_settings.indexing_batch_size == 0:
        ctx.logger.info(f"Indexing batch of {len(ctx.index_batch)} records...")

        ctx.db_session.commit()
        await CatalogRecord.bulk_index(ctx.index_batch)
        ctx.index_batch.clear()


async def handle_final_batch_snippet(ctx: ManagedTask):
    if not ctx.index_batch:
        return

    ctx.logger.info(
        f"Indexing final batch of {len(ctx.index_batch)} records..."
    )

    ctx.db_session.commit()
    await CatalogRecord.bulk_index(ctx.index_batch)
    ctx.index_batch.clear()
    await ctx.update_progress()


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

from typing import List

from aleph_nought import RecordStatus
from marcdantic import MarcRecord
from sqlalchemy.orm import Session

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.tasks import ManagedTask
from catalog_records.models import (
    FetchBatchOfRecordsData,
    FetchRecordData,
    SyncRecordsData,
)
from config import config
from entities.catalog_record import CatalogRecord


class AlephError(Exception):
    pass


def _save_record(
    db_session: Session,
    base: str,
    system_number: str,
    record: MarcRecord,
) -> CatalogRecord | None:
    catalog_record = CatalogRecord.find_by_base_and_system_number(
        db_session, base, system_number
    )

    if catalog_record:
        catalog_record.marc = record._marc
        catalog_record.deleted = False
        catalog_record.last_sync = config.timestamp
    else:
        catalog_record = CatalogRecord(
            base=base, system_number=system_number, marc=record._marc
        )

    catalog_record.save(db_session)


async def fetch_record_task(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = FetchRecordData.model_validate(ctx.task.data)
        base = data.base
        system_number = data.system_number

        client = AlephClientRegistry.get(base)

        if not client.OAI.is_available():
            raise AlephError("OAI service is not available")

        record = client.OAI.get_record(system_number)

        if record is None:
            ctx.logger.error(
                f"Record with system number '{system_number}' not found"
            )
            return

        await _save_record(ctx.db_session, base, system_number, record).index()


async def fetch_batch_of_records_task(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        progress_interval = ctx.task_settings.progress_update_interval
        batch_size = ctx.task_settings.indexing_batch_size
        data = FetchBatchOfRecordsData.model_validate(ctx.task.data)

        for fetch_base_data in data.per_base:
            base = fetch_base_data.base
            client = AlephClientRegistry.get(base)

            if not client.OAI.is_available():
                raise AlephError(f"OAI service for {base} is not available")

        progress = 0
        batch: List[CatalogRecord] = []

        for fetch_base_data in data.per_base:
            base = fetch_base_data.base
            client = AlephClientRegistry.get(base)

            for system_number in fetch_base_data.system_numbers:
                try:
                    record = client.OAI.get_record(system_number)

                    if record is None:
                        ctx.logger.error(
                            f"Record with system number '{system_number}' "
                            f"not found in base '{base}'"
                        )
                        continue

                    catalog_record = _save_record(
                        ctx.db_session, base, system_number, record
                    )

                    batch.append(catalog_record)
                    progress += 1

                    if progress % progress_interval == 0:
                        ctx.logger.info(f"Processed {progress} records so far")

                    if progress % batch_size == 0:
                        ctx.logger.info(
                            f"Indexing batch of {len(batch)} records..."
                        )

                        ctx.db_session.commit()
                        await CatalogRecord.bulk_index(batch)

                        batch = []

                except Exception as e:
                    ctx.logger.error(
                        f"Failed processing record {system_number}:\n{e}"
                    )

        if batch:
            ctx.logger.info(f"Indexing final batch of {len(batch)} records...")
            ctx.db_session.commit()
            await CatalogRecord.bulk_index(batch)

        ctx.logger.info(
            f"Finished catalog sync, total records processed: {progress}"
        )


def _process_record_from_sync(
    db_session: Session,
    base: str,
    system_number: str,
    status: RecordStatus,
    record: MarcRecord | None,
) -> CatalogRecord | None:
    """
    Update or delete a catalog record in the database based on its status.

    Parameters
    ----------
    db_session : Session
        SQLAlchemy database session used for querying and updating records.
    base : str
        The identifier of the catalog base.
    system_number : str
        The unique system number of the record.
    status : RecordStatus
        Status of the record,
        indicating whether it is Active, Deleted, or Failed.
    record : object
        The record object containing MARC data if the status is Active.

    Raises
    ------
    ValueError
        If the record status is Active but no MARC data is available.
    """
    if status == RecordStatus.Failed:
        raise ValueError(
            f"Failed fetching record {system_number} in base {base}."
        )

    if status == RecordStatus.Deleted:
        catalog_record = (
            db_session.query(CatalogRecord)
            .filter_by(base=base, system_number=system_number)
            .first()
        )
        if catalog_record:
            catalog_record.last_sync = config.timestamp
            catalog_record.deleted = True

        return catalog_record

    if not record:
        raise ValueError(
            f"Record {system_number} in base {base} has no MARC data."
        )

    catalog_record = CatalogRecord.find_by_base_and_system_number(
        db_session, base, system_number
    )

    if catalog_record:
        catalog_record.marc = record._marc
        catalog_record.last_sync = config.timestamp
    else:
        catalog_record = CatalogRecord(
            base=base, system_number=system_number, marc=record._marc
        )

    return catalog_record.save(db_session)


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

    Raises
    ------
    ValueError
        If a sync task is already running for the given base, or
        if the OAI service is not available for the base.
    """
    async with ManagedTask(
        task_id=task_id,
        lock_key=lock_key,
        lock_blocking_timeout=lock_blocking_timeout,
    ) as ctx:
        progress_interval = ctx.task_settings.progress_update_interval
        batch_size = ctx.task_settings.indexing_batch_size

        data = SyncRecordsData.model_validate(ctx.task.data)

        base = data.base
        from_date = data.from_date

        ctx.logger.info(f"Starting catalog sync for base '{base}'")

        client = AlephClientRegistry.get(base)

        if not client.OAI.is_available():
            raise ValueError(f"OAI service is not available for base {base}")

        progress = 0
        batch: List[CatalogRecord] = []

        for base, system_number, status, record in client.OAI.list_records(
            from_date, None
        ):
            try:
                record = _process_record_from_sync(
                    ctx.db_session, base, system_number, status, record
                )
                if record is None:
                    # Record was marked as deleted but did not exist locally
                    continue

                batch.append(record)
                progress += 1

                if progress % progress_interval == 0:
                    ctx.logger.info(f"Processed {progress} records so far")

                if progress % batch_size == 0:
                    ctx.logger.info(
                        f"Indexing batch of {len(batch)} records..."
                    )

                    ctx.db_session.commit()
                    await CatalogRecord.bulk_index(batch)

                    batch = []

            except Exception as e:
                ctx.logger.error(
                    f"Failed processing record {system_number}:\n{e}"
                )

        if batch:
            ctx.logger.info(f"Indexing final batch of {len(batch)} records...")
            ctx.db_session.commit()
            await CatalogRecord.bulk_index(batch)

        ctx.logger.info(
            f"Finished catalog sync, total records processed: {progress}"
        )

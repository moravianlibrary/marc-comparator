from adapters.analytics import sync_records
from adapters.tasks import ManagedTask


async def recreate_indexes(
    task_id: str, lock_key: str, lock_blocking_timeout: int
) -> None:
    """
    Trigger a full ClickHouse sync (replaces the old ES index recreation).
    """
    async with ManagedTask(
        task_id=task_id,
        lock_key=lock_key,
        lock_blocking_timeout=lock_blocking_timeout,
    ) as ctx:
        ctx.logger.info("Starting full ClickHouse sync.")

        count = sync_records(ctx.db_session)

        ctx.logger.info(
            f"Full ClickHouse sync completed. Synced {count} records."
        )

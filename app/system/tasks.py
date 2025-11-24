from esorm import es, setup_mappings
from sqlalchemy.orm.attributes import InstrumentedAttribute

from adapters.database import Base
from adapters.indexer import IndexerSchema
from adapters.tasks import ManagedTask, TaskContext
from entities.catalog_record import CatalogRecord
from entities.task import Task


async def _recreate_index(
    ctx: TaskContext,
    db_model: type[Base],
    indexer_schema: type[IndexerSchema],
    order_by_column: InstrumentedAttribute,
):
    """
    Recreate the index for a given DB model in batches using keyset pagination.

    Parameters
    ----------
    ctx : TaskContext
        Managed task context containing db session, indexer, logger, etc.
    db_model :
        SQLAlchemy model class
    indexer_schema :
        IndexerSchema class
    order_by_column :
        Column to use for ordering and keyset pagination
    """
    name = db_model.__name__
    index_name = indexer_schema.ESConfig.index

    total = ctx.db_session.query(db_model).count()

    ctx.logger.info(f"Starting indexing for {name}: {total} items to process.")

    if await es.indices.exists(index=index_name):
        try:
            await es.indices.delete(index=index_name)
        except Exception as e:
            ctx.logger.error(f"Error deleting index for {name}: {e}")
            return

    try:
        await setup_mappings()
    except Exception as e:
        ctx.logger.error(f"Error setting up index for {name}: {e}")
        return

    offset = 0
    last_reported = 0
    while offset < total:
        batch = (
            ctx.db_session.query(db_model)
            .order_by(order_by_column)
            .offset(offset)
            .limit(ctx.task_settings.indexing_batch_size)
            .all()
        )

        if not batch:
            ctx.logger.warning(
                f"Empty batch encountered for {name} "
                f"at offset {offset}. Stopping indexing."
            )
            break

        try:
            await db_model.bulk_index(batch)
        except Exception as e:
            ctx.logger.error(
                f"Error indexing batch at offset {offset} for {name}: {e}"
            )
            return

        offset += len(batch)

        if (
            offset - last_reported
            >= ctx.task_settings.progress_update_interval
        ):
            last_reported = offset
            ctx.logger.info(f"Indexed {offset}/{total} catalog records")

    ctx.logger.info(f"Completed indexing for {name}.")


async def recreate_indexes(
    task_id: str, lock_key: str, lock_blocking_timeout: int
) -> None:
    """
    Recreate indexes for CatalogRecord and Task models.
    """
    async with ManagedTask(
        task_id=task_id,
        lock_key=lock_key,
        lock_blocking_timeout=lock_blocking_timeout,
    ) as ctx:
        ctx.logger.info("Starting full index recreation task.")

        await _recreate_index(
            ctx,
            CatalogRecord,
            CatalogRecord.__indexer_schema__,
            CatalogRecord.latest_sync,
        )

        await _recreate_index(
            ctx,
            Task,
            Task.__indexer_schema__,
            Task.created_at,
        )

        ctx.logger.info("Full index recreation task completed.")

from adapters.indexer import IndexerQuery
from adapters.tasks import ManagedTask
from entities.task import Task


async def delete_tasks(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        query = IndexerQuery.model_validate(ctx.task.data)

        async for task in Task.get_by_query(ctx.db_session, query):
            try:
                task.delete(ctx.db_session)

                ctx.index_batch.append(task)
                ctx.progress += 1

                if (
                    ctx.progress % ctx.task_settings.progress_update_interval
                    == 0
                ):
                    ctx.logger.info(
                        f"Processed {ctx.progress} records so far."
                    )

                if ctx.progress % ctx.task_settings.indexing_batch_size == 0:
                    ctx.logger.info(
                        f"Deleting batch of {len(ctx.index_batch)} tasks "
                        "from index..."
                    )

                    await Task.bulk_delete(ctx.index_batch)
                    ctx.index_batch.clear()

            except Exception as e:
                ctx.logger.error(
                    f"Failed to delete task {task.id} from index:\n{e}"
                )

        if not ctx.index_batch:
            return

        ctx.logger.info(
            f"Deleting final batch of {len(ctx.index_batch)} tasks "
            "from index..."
        )

        await Task.bulk_delete(ctx.index_batch)
        ctx.index_batch.clear()

        ctx.logger.info(
            f"Finished deleting, total tasks processed: {ctx.progress}"
        )

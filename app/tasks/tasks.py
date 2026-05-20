from adapters.tasks import ManagedTask, handle_batch_progress_snippet
from entities.task import Task, TaskStatus


async def delete_tasks(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        # Delete all completed/failed/revoked tasks (not the current one)
        tasks = (
            ctx.db_session.query(Task)
            .filter(
                Task.status.in_([
                    TaskStatus.Success,
                    TaskStatus.Failure,
                    TaskStatus.Revoked,
                ]),
                Task.task_id != ctx.task.task_id,
            )
            .all()
        )

        for task in tasks:
            try:
                task.delete(ctx.db_session)
                handle_batch_progress_snippet(ctx)
            except Exception as e:
                ctx.logger.error(
                    f"Failed to delete task {task.task_id}:\n{e}"
                )

        ctx.logger.info(
            f"Finished deleting, total tasks processed: {ctx.progress}"
        )

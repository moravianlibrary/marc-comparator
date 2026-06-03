from datetime import UTC, datetime, timedelta

from adapters.tasks import ManagedTask, handle_batch_progress_snippet, handle_final_batch_snippet
from entities.task import Task, TaskStatus


async def delete_tasks(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        max_age_days = ctx.task.data.get("max_age_days") if ctx.task.data else None

        query = ctx.db_session.query(Task).filter(
            Task.status.in_(
                [
                    TaskStatus.Success,
                    TaskStatus.Failure,
                    TaskStatus.Revoked,
                ]
            ),
            Task.task_id != ctx.task.task_id,
        )

        if max_age_days is not None:
            cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
            query = query.filter(Task.created_at < cutoff)
            ctx.logger.info(
                f"Deleting tasks older than {max_age_days} days (before {cutoff.isoformat()})."
            )
        else:
            ctx.logger.info("Deleting all completed/failed/revoked tasks.")

        tasks = query.all()
        ctx.total = len(tasks)

        for task in tasks:
            try:
                task.delete(ctx.db_session, commit=False)
                handle_batch_progress_snippet(ctx)
            except Exception as e:
                ctx.db_session.rollback()
                ctx.logger.error(f"Failed to delete task {task.task_id}:\n{e}")
                handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(f"Finished deleting, total tasks processed: {ctx.progress}")

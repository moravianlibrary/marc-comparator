from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.task import Task, TaskSchema, TaskType


async def recreate_indexes(
    created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Recreating indexes",
            type=TaskType.RecreateIndexes,
            created_by=created_by,
        ),
        db_session,
    )

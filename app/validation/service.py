from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.task import Task, TaskSchema, TaskType


async def validate_record(
    query: dict, user_id: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Validate records",
            type=TaskType.ValidateRecords,
            created_by=user_id,
            data={"query": query}
        ), 
        db_session
    )

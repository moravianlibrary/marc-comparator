from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.task import Task, TaskSchema, TaskType

from .models import CreateReportData


async def create_report(
    data: CreateReportData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name=f"Generating report for {data.tool}",
            type=TaskType.CreateReport,
            created_by=created_by,
            data=data.model_dump(mode="json"),
        ),
        db_session,
    )

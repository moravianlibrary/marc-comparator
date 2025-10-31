from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.settings import SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.service import get_settings_part

from .models import ComparisonTaskData


async def compare(
    data: ComparisonTaskData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    # Ensure settings exist
    get_settings_part(
        SettingsScope.Comparison, data.comparator.value, db_session
    )

    return await enqueue_task(
        Task(
            name=f"Comparing records using {data.comparator.value} comparator",
            type=TaskType.CompareRecords,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

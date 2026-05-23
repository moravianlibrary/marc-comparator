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
    # Ensure comparison settings exist
    get_settings_part(
        SettingsScope.Comparison, "comparator", db_session
    )

    return await enqueue_task(
        Task(
            name=(
                "Comparing records "
                f"against authority records from '{data.target_base}' base"
            ),
            type=TaskType.CompareRecords,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

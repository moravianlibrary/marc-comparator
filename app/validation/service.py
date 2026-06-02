from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.settings import SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.service import get_settings_part

from .models import ValidationTaskData


async def validate(
    data: ValidationTaskData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    # Ensure settings exist
    for validator in data.validators:
        get_settings_part(SettingsScope.Validation, validator.value, db_session)

    return await enqueue_task(
        Task(
            name=f"Validating records using {len(data.validators)} validators",
            type=TaskType.ValidateRecords,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

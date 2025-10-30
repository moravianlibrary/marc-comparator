from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from common.exceptions import SettingsNotFoundError, SettingsPartNotFoundError
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskType

from .models import ValidationSettings, ValidationTaskData


def get_settings(
    db_session: DatabaseSession,
) -> ValidationSettings | None:
    settings = Settings.get(
        db_session,
        SettingsScope.Validation,
        ValidationSettings,
    )

    if settings is None:
        raise SettingsNotFoundError(SettingsScope.Validation)

    return settings


def set_settings(
    settings: ValidationSettings, db_session: DatabaseSession
) -> ValidationSettings:
    return Settings.save(
        db_session,
        SettingsScope.Validation,
        settings,
        ValidationSettings,
    )


async def compare(
    data: ValidationTaskData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    # Ensure settings exist
    settings = get_settings(db_session)

    for validator in data.validators:
        if settings[validator.value] is None:
            raise SettingsPartNotFoundError(
                SettingsScope.Validation, validator.value
            )

    return await enqueue_task(
        Task(
            name=f"Comparing records using {len(data.validators)} validators",
            type=TaskType.ValidateRecords,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

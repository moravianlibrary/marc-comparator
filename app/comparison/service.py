from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.exceptions import (
    SettingsNotFoundError,
    SettingsPartNotFoundError,
)

from .models import ComparisonSettings, ComparisonTaskData


def get_settings(
    db_session: DatabaseSession,
) -> ComparisonSettings | None:
    settings = Settings.get(
        db_session,
        SettingsScope.Comparison,
        ComparisonSettings,
    )

    if settings is None:
        raise SettingsNotFoundError(SettingsScope.Comparison)

    return settings


def set_settings(
    settings: ComparisonSettings, db_session: DatabaseSession
) -> ComparisonSettings:
    return Settings.save(
        db_session,
        SettingsScope.Comparison,
        settings,
        ComparisonSettings,
    )


async def compare(
    data: ComparisonTaskData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    # Ensure settings exist
    settings = get_settings(db_session)

    if settings[data.comparator.value] is None:
        raise SettingsPartNotFoundError(
            SettingsScope.Comparison, data.comparator.value
        )

    return await enqueue_task(
        Task(
            name=f"Comparing records using {data.comparator.value} comparator",
            type=TaskType.Comparison,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

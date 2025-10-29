from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskType

from .models import AuthorityLinkingSettings, AuthorityLinkingTaskData


def get_settings(
    db_session: DatabaseSession,
) -> AuthorityLinkingSettings | None:
    return Settings.get(
        db_session,
        SettingsScope.AuthorityLinking,
        AuthorityLinkingSettings,
    )


def set_settings(
    settings: AuthorityLinkingSettings, db_session: DatabaseSession
) -> AuthorityLinkingSettings:
    return Settings.save(
        db_session,
        SettingsScope.AuthorityLinking,
        settings,
        AuthorityLinkingSettings,
    )


async def authority_linking(
    data: AuthorityLinkingTaskData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name=f"Authority linking for base '{data.target_base}'",
            type=TaskType.AuthorityLinking,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

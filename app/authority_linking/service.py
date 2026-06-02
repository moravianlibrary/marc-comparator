from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.settings import SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.service import get_settings_part

from .models import AuthorityLinkingTaskData


async def authority_linking(
    data: AuthorityLinkingTaskData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    for linker in data.linkers:
        get_settings_part(SettingsScope.AuthorityLinking, linker.value, db_session)

    return await enqueue_task(
        Task(
            name=f"Authority linking for base '{data.target_base}'",
            type=TaskType.LinkRecordsToAuthorities,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )

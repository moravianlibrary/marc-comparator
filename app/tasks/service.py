from fastapi import HTTPException, status
from fastapi.responses import PlainTextResponse

from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from adapters.tasks import revoke_task as execute_task_revoke
from entities.role import Permission
from entities.task import Task, TaskSchema, TaskStatus, TaskType
from entities.user import User
from tasks.models import TracebackLinesRequestParams


def get_traceback_lines(
    task_id: str,
    params: TracebackLinesRequestParams,
    user_id: str,
    db_session: DatabaseSession,
) -> PlainTextResponse:
    task = Task.get(db_session, task_id)
    user = User.get(db_session, user_id)

    if (
        Permission.ManageAllTasks not in user.permissions
        and str(task.created_by) != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this task.",
        )

    lines = task.traceback.splitlines() if task.traceback else []
    start = params.start_line or 0
    end = params.end_line or len(lines)

    return PlainTextResponse(
        "\n".join(lines[start:end]), media_type="text/plain"
    )


async def revoke_task(
    task_id: str, user_id: str, db_session: DatabaseSession
) -> TaskSchema:
    task = Task.get(db_session, task_id)
    user = User.get(db_session, user_id)

    if (
        Permission.ManageAllTasks not in user.permissions
        and str(task.created_by) != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to revoke this task.",
        )

    if task.status not in {TaskStatus.Started, TaskStatus.Pending}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with status '{task.status}' cannot be revoked.",
        )

    return await execute_task_revoke(task, db_session)


async def delete_tasks(
    created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Deleting tasks",
            type=TaskType.DeleteTasks,
            created_by=created_by,
        ),
        db_session,
    )

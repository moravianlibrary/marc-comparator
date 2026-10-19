import uuid

from entities.task import Task, TaskSchema, TaskType
from entities.user import SYSTEM_USER_ID


def test_task_schema_accepts_the_system_user_that_creates_scheduled_tasks():
    task = Task(
        task_id=uuid.uuid4(),
        name="Scheduled maintenance",
        type=TaskType.CleanupStaleLocks,
        created_by=SYSTEM_USER_ID,
        progress=0,
    )

    result = TaskSchema.model_validate(task, from_attributes=True)

    assert result.created_by == SYSTEM_USER_ID

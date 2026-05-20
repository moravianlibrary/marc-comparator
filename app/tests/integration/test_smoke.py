import pytest

from adapters.database import DatabaseSession
from adapters.lock_server import one_at_a_time_lock
from adapters.tasks import enqueue_task
from auth.models import TokenData
from entities.task import Task, TaskType


@pytest.mark.asyncio
async def test_one_at_a_time_lock(lock_server_client):
    lock_name = "test-lock"

    with one_at_a_time_lock(lock_name) as lock1:
        assert lock1 is not None

        with one_at_a_time_lock(lock_name, blocking=False) as lock2:
            assert lock2 is None

    with one_at_a_time_lock(lock_name) as lock3:
        assert lock3 is not None


@pytest.mark.asyncio
async def test_tasks_client_smoke(
    db_session: DatabaseSession,
    user: TokenData,
    tasks_client,
):
    task = Task(
        name="Test Task",
        type=TaskType.SyncRecords,
        created_by=user.user_id,
        data={"base": "TEST"},
    )
    await enqueue_task(task, db_session)


@pytest.mark.asyncio
async def test_aleph_client_registry_smoke(aleph_client_registry):
    from adapters.aleph_client_registry import AlephClientRegistry

    assert AlephClientRegistry.get("TEST") is not None

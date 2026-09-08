"""Integration tests for Workstream 1 task resilience: the poison-message
guard (bounded redeliveries under acks_late) and the orphaned-task reaper."""

from datetime import timedelta

import pytest

from adapters.database import DatabaseSession
from adapters.tasks import (
    MAX_TASK_ATTEMPTS,
    REAPER_HEARTBEAT_TIMEOUT,
    ManagedTask,
    PoisonPillError,
    reap_orphaned_tasks,
)
from auth.models import TokenData
from config import config
from entities.task import Task, TaskStatus, TaskType


def _make_task(db_session, user, **kwargs) -> Task:
    task = Task(
        name="Resilience test task",
        type=TaskType.FetchRecord,
        created_by=user.user_id,
        **kwargs,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestPoisonGuard:
    @pytest.mark.asyncio
    async def test_task_over_max_attempts_is_failed(
        self, db_session: DatabaseSession, user: TokenData
    ):
        # Already at the limit: the next entry pushes it over and must poison.
        task = _make_task(db_session, user, attempts=MAX_TASK_ATTEMPTS)
        task_id = task.task_id

        with pytest.raises(PoisonPillError):
            async with ManagedTask(task_id=str(task_id)):
                pass  # body must never run

        db_session.expire_all()
        reloaded = db_session.get(Task, task_id)
        assert reloaded is not None
        assert reloaded.status == TaskStatus.Failure
        assert reloaded.attempts == MAX_TASK_ATTEMPTS + 1
        assert "Poison message" in (reloaded.traceback or "")

    @pytest.mark.asyncio
    async def test_normal_run_increments_attempts(
        self, db_session: DatabaseSession, user: TokenData
    ):
        task = _make_task(db_session, user, attempts=0)
        task_id = task.task_id

        async with ManagedTask(task_id=str(task_id)) as ctx:
            ctx.total = 1

        db_session.expire_all()
        reloaded = db_session.get(Task, task_id)
        assert reloaded is not None
        assert reloaded.status == TaskStatus.Success
        assert reloaded.attempts == 1


class TestOrphanReaper:
    def _stale(self):
        return config.timestamp - timedelta(seconds=REAPER_HEARTBEAT_TIMEOUT + 60)

    def _patch(self, mocker, db_session, active):
        # reaper opens its own SessionLocal() and inspects live workers; point
        # both at the test session and a controlled active-set.
        mocker.patch("adapters.database.SessionLocal", lambda: db_session)
        inspect_result = mocker.Mock()
        inspect_result.active.return_value = active
        mocker.patch("adapters.tasks.tasks_client.control.inspect", return_value=inspect_result)

    def test_stale_started_task_is_reaped(self, db_session, user, mocker):
        task = _make_task(
            db_session,
            user,
            status=TaskStatus.Started,
            started_at=self._stale(),
            heartbeat=self._stale(),
        )
        task_id = task.task_id
        self._patch(mocker, db_session, active=None)  # no live workers

        reap_orphaned_tasks()

        db_session.expire_all()
        reloaded = db_session.get(Task, task_id)
        assert reloaded is not None
        assert reloaded.status == TaskStatus.Failure
        assert "no heartbeat" in (reloaded.traceback or "")

    def test_fresh_heartbeat_task_is_not_reaped(self, db_session, user, mocker):
        task = _make_task(
            db_session,
            user,
            status=TaskStatus.Started,
            started_at=self._stale(),
            heartbeat=config.timestamp,
        )
        task_id = task.task_id
        self._patch(mocker, db_session, active=None)

        reap_orphaned_tasks()

        db_session.expire_all()
        assert db_session.get(Task, task_id).status == TaskStatus.Started

    def test_active_task_is_not_reaped(self, db_session, user, mocker):
        # Stale heartbeat but still executing on a worker -> both conditions
        # not met, so it must survive.
        task = _make_task(
            db_session,
            user,
            status=TaskStatus.Started,
            started_at=self._stale(),
            heartbeat=self._stale(),
        )
        task_id = task.task_id
        active = {"worker@host": [{"id": str(task_id)}]}
        self._patch(mocker, db_session, active=active)

        reap_orphaned_tasks()

        db_session.expire_all()
        assert db_session.get(Task, task_id).status == TaskStatus.Started

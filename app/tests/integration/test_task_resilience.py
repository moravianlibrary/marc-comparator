"""Integration tests for Workstream 1 task resilience: the poison-message
guard (bounded redeliveries under acks_late) and the orphaned-task reaper."""

from datetime import timedelta

import pytest
from sqlalchemy import text

from adapters.database import DatabaseSession
from adapters.tasks import (
    MAX_TASK_ATTEMPTS,
    REAPER_HEARTBEAT_TIMEOUT,
    ManagedTask,
    PoisonPillError,
    TaskRevokedError,
    reap_orphaned_tasks,
    revoke_task,
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


class TestRevokedGuard:
    """A revoked task must not run because its message came back."""

    @staticmethod
    def reload(db_session, task_id) -> Task:
        db_session.expire_all()
        reloaded = db_session.get(Task, task_id)
        assert reloaded is not None
        return reloaded

    @pytest.mark.asyncio
    async def test_a_revoked_task_is_not_started(
        self, db_session: DatabaseSession, user: TokenData
    ):
        # acks_late redelivers whatever the killed worker was holding, and the
        # worker it lands on never heard the revoke.
        task = _make_task(db_session, user, status=TaskStatus.Revoked)
        task_id = task.task_id

        with pytest.raises(TaskRevokedError):
            async with ManagedTask(task_id=str(task_id)):
                pytest.fail("a revoked task ran")

        assert self.reload(db_session, task_id).status == TaskStatus.Revoked

    @pytest.mark.asyncio
    async def test_the_revoked_row_is_left_exactly_as_it_was(
        self, db_session: DatabaseSession, user: TokenData
    ):
        task = _make_task(
            db_session, user, status=TaskStatus.Revoked, finished_at=config.timestamp, attempts=1
        )
        task_id = task.task_id

        with pytest.raises(TaskRevokedError):
            async with ManagedTask(task_id=str(task_id)):
                pass

        reloaded = self.reload(db_session, task_id)
        # Not restarted, not re-attempted, not re-finished.
        assert reloaded.status == TaskStatus.Revoked
        assert reloaded.attempts == 1
        assert reloaded.started_at is None

    @pytest.mark.asyncio
    async def test_a_task_that_was_not_revoked_still_runs(
        self, db_session: DatabaseSession, user: TokenData
    ):
        task = _make_task(db_session, user, status=TaskStatus.Pending)
        task_id = task.task_id

        async with ManagedTask(task_id=str(task_id)) as ctx:
            assert ctx.task.status == TaskStatus.Started

        assert self.reload(db_session, task_id).status == TaskStatus.Success

    @pytest.mark.asyncio
    async def test_the_run_lock_is_not_left_held(
        self, db_session: DatabaseSession, user: TokenData, lock_server_client
    ):
        from adapters.lock_server import get_active_locks

        task = _make_task(db_session, user, status=TaskStatus.Revoked)
        lock_key = f"task-run-{task.task_id}"

        with pytest.raises(TaskRevokedError):
            async with ManagedTask(task_id=str(task.task_id), lock_key=lock_key):
                pass

        assert lock_key not in get_active_locks()

    @pytest.mark.asyncio
    async def test_revoking_a_sync_keeps_its_worker_alive_for_lock_cleanup(
        self, db_session: DatabaseSession, user: TokenData, mocker
    ):
        task = Task(
            name="Sync cancellation test",
            created_by=user.user_id,
            type=TaskType.SyncRecords,
            status=TaskStatus.Started,
            data={"base": "TEST"},
        )
        db_session.add(task)
        db_session.commit()
        revoke = mocker.patch("adapters.tasks.tasks_client.control.revoke")

        await revoke_task(task, db_session)

        assert self.reload(db_session, task.task_id).status == TaskStatus.Revoked
        revoke.assert_called_once_with(str(task.task_id), terminate=False, signal="SIGTERM")

    @pytest.mark.asyncio
    async def test_sync_lock_is_released_after_graceful_revoke(
        self, db_session: DatabaseSession, user: TokenData, lock_server_client, mocker
    ):
        from adapters.lock_server import get_active_locks

        task = Task(
            name="Active sync cancellation test",
            created_by=user.user_id,
            type=TaskType.SyncRecords,
            data={"base": "TEST"},
        )
        db_session.add(task)
        db_session.commit()
        lock_key = "catalog_sync_TEST"
        mocker.patch("adapters.tasks.tasks_client.control.revoke")

        async with ManagedTask(task_id=str(task.task_id), lock_key=lock_key):
            assert lock_key in get_active_locks()
            db_session.refresh(task)
            await revoke_task(task, db_session)

        assert lock_key not in get_active_locks()
        assert self.reload(db_session, task.task_id).status == TaskStatus.Revoked


class TestFinalAnalyticsRebuild:
    @pytest.mark.asyncio
    async def test_a_failed_rebuild_keeps_the_success(
        self, db_session: DatabaseSession, user: TokenData, mocker
    ):
        # The rebuild runs after the work is done; losing its connection used
        # to roll the uncommitted Success back, and the reaper then failed a
        # run that had finished.
        task = _make_task(db_session, user)
        task.type = TaskType.ProcessRecords
        db_session.commit()
        task_id = task.task_id

        def rebuild_all(session):
            # Fail the way a dropped connection does: inside the session's
            # transaction, leaving it unusable until rolled back.
            session.execute(text("SELECT 1 / 0"))

        rebuild = mocker.patch("catalog_records.analytics.rebuild_all", side_effect=rebuild_all)

        async with ManagedTask(task_id=str(task_id)) as ctx:
            ctx.total = 1

        rebuild.assert_called_once()
        db_session.expire_all()
        reloaded = db_session.get(Task, task_id)
        assert reloaded is not None
        assert reloaded.status == TaskStatus.Success
        assert reloaded.finished_at is not None

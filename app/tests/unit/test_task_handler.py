from unittest.mock import MagicMock, patch, call

from adapters.tasks import ManagedTask, TaskHandler, handle_batch_progress_snippet
from entities.task import Task, TaskStatus, TaskType
from tasks.models import TaskSettings


class TestFlushTraceback:
    def test_flush_traceback_does_not_commit(self):
        """_flush_traceback should flush the session, not commit it."""
        db_session = MagicMock()
        task = MagicMock()
        managed_task = MagicMock()
        managed_task.before_commit = None

        handler = TaskHandler(db_session, task, managed_task)
        handler._flush_traceback()

        db_session.flush.assert_called_once()
        db_session.commit.assert_not_called()

    def test_flush_traceback_does_not_call_before_commit(self):
        """_flush_traceback should not call before_commit — that's for commit boundaries only."""
        db_session = MagicMock()
        task = MagicMock()
        managed_task = MagicMock()
        managed_task.before_commit = MagicMock()

        handler = TaskHandler(db_session, task, managed_task)
        handler._flush_traceback()

        managed_task.before_commit.assert_not_called()
        db_session.flush.assert_called_once()


class TestSaveTask:
    def test_save_task_does_not_commit(self):
        """save_task must flush (not commit) so that commit boundaries control persistence."""
        ctx = ManagedTask(task_id="fake-id")
        ctx.db_session = MagicMock()
        ctx.task = MagicMock()

        ctx.save_task()

        ctx.task.save.assert_called_once_with(ctx.db_session, commit=False)


class TestBatchProgressSnippet:
    def _make_ctx(self, settings: TaskSettings, before_commit=None):
        ctx = ManagedTask(task_id="fake-id")
        ctx.db_session = MagicMock()
        ctx.logger = MagicMock()
        ctx.task = MagicMock()
        ctx.task.type = MagicMock()
        ctx.task.task_id = "fake-id"
        ctx.task.progress = None
        ctx.task.created_by = "fake-user"
        ctx.task_settings = settings
        ctx._total = 1000
        ctx.progress = 0
        ctx.before_commit = before_commit
        ctx.cycle_session = MagicMock()
        return ctx

    def test_progress_update_does_not_commit(self):
        """At progress_update_interval, only flush + WS event, no commit."""
        settings = TaskSettings(
            progress_update_interval=1,
            commit_interval=1000,
            sector_flush_interval=1000,
        )
        ctx = self._make_ctx(settings)

        handle_batch_progress_snippet(ctx)

        ctx.db_session.commit.assert_not_called()

    def test_commit_interval_cycles_session_for_regular_tasks(self):
        """At commit_interval (no before_commit), cycle_session should be called."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1,
            sector_flush_interval=1000,
        )
        ctx = self._make_ctx(settings)

        handle_batch_progress_snippet(ctx)

        ctx.cycle_session.assert_called_once()
        ctx.db_session.commit.assert_not_called()

    def test_commit_interval_ignored_when_before_commit_set(self):
        """When before_commit is set, commit_interval should not trigger cycle_session."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1,
            sector_flush_interval=1000,
        )
        before_commit = MagicMock()
        ctx = self._make_ctx(settings, before_commit=before_commit)

        handle_batch_progress_snippet(ctx)

        ctx.cycle_session.assert_not_called()
        ctx.db_session.commit.assert_not_called()
        before_commit.assert_not_called()

    def test_sector_flush_interval_cycles_session(self):
        """At sector_flush_interval (with before_commit), cycle_session should be called."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1000,
            sector_flush_interval=1,
        )
        before_commit = MagicMock()
        ctx = self._make_ctx(settings, before_commit=before_commit)

        handle_batch_progress_snippet(ctx)

        ctx.cycle_session.assert_called_once()
        ctx.db_session.commit.assert_not_called()

    def test_sector_flush_interval_ignored_when_no_before_commit(self):
        """When before_commit is not set, sector_flush_interval should not trigger cycle_session."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1000,
            sector_flush_interval=1,
        )
        ctx = self._make_ctx(settings)

        handle_batch_progress_snippet(ctx)

        ctx.cycle_session.assert_not_called()
        ctx.db_session.commit.assert_not_called()


class TestBatchProgressCycling:
    def test_commit_interval_cycles_session(self):
        """At commit_interval (regular task), cycle_session should be called."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1,
            sector_flush_interval=1000,
        )
        ctx = ManagedTask(task_id="fake-id")
        ctx.db_session = MagicMock()
        ctx.task = MagicMock()
        ctx.task.type = MagicMock()
        ctx.task_settings = settings
        ctx._total = 1000
        ctx.progress = 0
        ctx.before_commit = None
        ctx.cycle_session = MagicMock()

        handle_batch_progress_snippet(ctx)

        ctx.cycle_session.assert_called_once()

    def test_sector_flush_interval_cycles_session(self):
        """At sector_flush_interval (record-writing task), cycle_session should be called."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1000,
            sector_flush_interval=1,
        )
        ctx = ManagedTask(task_id="fake-id")
        ctx.db_session = MagicMock()
        ctx.task = MagicMock()
        ctx.task.type = MagicMock()
        ctx.task_settings = settings
        ctx._total = 1000
        ctx.progress = 0
        ctx.before_commit = MagicMock()
        ctx.cycle_session = MagicMock()

        handle_batch_progress_snippet(ctx)

        ctx.cycle_session.assert_called_once()


class TestCycleSession:
    def test_cycle_session_closes_old_and_opens_new(self):
        """cycle_session should close the old session and open a new one."""
        old_session = MagicMock()
        new_session = MagicMock()

        task = Task(
            name="Test",
            type=TaskType.FetchRecord,
            created_by="12345678-1234-4678-9abc-1234567890ab",
        )
        task.task_id = "fake-task-id"

        reloaded_task = MagicMock()
        reloaded_task.task_id = "fake-task-id"
        new_session.get.return_value = reloaded_task

        ctx = ManagedTask(task_id="fake-task-id")
        ctx.db_session = old_session
        ctx.task = task
        ctx.before_commit = None

        # Mock the TaskHandler
        handler = MagicMock()
        ctx._handler = handler

        with patch("adapters.tasks.get_db_session", return_value=new_session):
            ctx.cycle_session()

        old_session.commit.assert_called_once()
        old_session.close.assert_called_once()
        assert ctx.db_session is new_session
        assert ctx.task is reloaded_task
        assert handler.db_session is new_session
        assert handler.task is reloaded_task

    def test_cycle_session_calls_before_commit(self):
        """cycle_session should call before_commit before committing."""
        old_session = MagicMock()
        new_session = MagicMock()
        new_session.get.return_value = MagicMock()

        ctx = ManagedTask(task_id="fake-task-id")
        ctx.db_session = old_session
        ctx.task = MagicMock()
        ctx.task.task_id = "fake-task-id"
        ctx._handler = MagicMock()

        call_order = []
        ctx.before_commit = lambda: call_order.append("before_commit")
        old_session.commit = lambda: call_order.append("commit")

        with patch("adapters.tasks.get_db_session", return_value=new_session):
            ctx.cycle_session()

        assert call_order == ["before_commit", "commit"]

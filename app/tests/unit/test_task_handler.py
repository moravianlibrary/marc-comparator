from unittest.mock import MagicMock

from adapters.tasks import ManagedTask, TaskHandler, handle_batch_progress_snippet
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

    def test_commit_interval_commits_for_regular_tasks(self):
        """At commit_interval (no before_commit), commit the session."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1,
            sector_flush_interval=1000,
        )
        ctx = self._make_ctx(settings)

        handle_batch_progress_snippet(ctx)

        ctx.db_session.commit.assert_called_once()

    def test_commit_interval_ignored_when_before_commit_set(self):
        """When before_commit is set, commit_interval should not trigger commits."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1,
            sector_flush_interval=1000,
        )
        before_commit = MagicMock()
        ctx = self._make_ctx(settings, before_commit=before_commit)

        handle_batch_progress_snippet(ctx)

        ctx.db_session.commit.assert_not_called()
        before_commit.assert_not_called()

    def test_sector_flush_interval_flushes_and_commits(self):
        """At sector_flush_interval (with before_commit), flush sectors then commit."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1000,
            sector_flush_interval=1,
        )
        call_order = []
        before_commit = lambda: call_order.append("before_commit")

        ctx = self._make_ctx(settings, before_commit=before_commit)
        ctx.db_session.commit = lambda: call_order.append("commit")

        handle_batch_progress_snippet(ctx)

        assert call_order == ["before_commit", "commit"]

    def test_sector_flush_interval_ignored_when_no_before_commit(self):
        """When before_commit is not set, sector_flush_interval should not trigger."""
        settings = TaskSettings(
            progress_update_interval=1000,
            commit_interval=1000,
            sector_flush_interval=1,
        )
        ctx = self._make_ctx(settings)

        handle_batch_progress_snippet(ctx)

        ctx.db_session.commit.assert_not_called()

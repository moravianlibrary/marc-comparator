from unittest.mock import MagicMock

from adapters.tasks import TaskHandler


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

from unittest.mock import MagicMock, patch

import pytest

from entities.task import Task, TaskStatus, TaskType


class TestEnqueueTask:
    @pytest.mark.asyncio
    async def test_dispatch_failure_marks_task_as_failed(self):
        """If dispatch_task raises, the task should be marked as Failure."""
        from adapters.tasks import enqueue_task

        db_session = MagicMock()
        task = Task(
            name="Test task",
            type=TaskType.FetchRecord,
            created_by="12345678-1234-4678-9abc-1234567890ab",
        )

        with patch("adapters.tasks.dispatch_task", side_effect=ConnectionError("broker down")):
            with pytest.raises(ConnectionError):
                await enqueue_task(task, db_session)

        assert task.status == TaskStatus.Failure
        assert task.finished_at is not None
        assert "Failed to dispatch" in task.traceback

    @pytest.mark.asyncio
    async def test_dispatch_failure_publishes_failure_event(self):
        """On dispatch failure, a task_status event with Failure should be published."""
        from adapters.tasks import enqueue_task

        db_session = MagicMock()
        task = Task(
            name="Test task",
            type=TaskType.FetchRecord,
            created_by="12345678-1234-4678-9abc-1234567890ab",
        )

        with (
            patch("adapters.tasks.dispatch_task", side_effect=ConnectionError("broker down")),
            patch("adapters.tasks.publish_event") as mock_publish,
        ):
            with pytest.raises(ConnectionError):
                await enqueue_task(task, db_session)

        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.status == "Failure"
        assert event.task_id == str(task.task_id)

    @pytest.mark.asyncio
    async def test_successful_dispatch_publishes_pending_event(self):
        """On successful dispatch, a task_status event with Pending should be published."""
        from adapters.tasks import enqueue_task

        db_session = MagicMock()
        task = Task(
            name="Test task",
            type=TaskType.FetchRecord,
            created_by="12345678-1234-4678-9abc-1234567890ab",
        )

        with (
            patch("adapters.tasks.dispatch_task"),
            patch("adapters.tasks.publish_event") as mock_publish,
        ):
            await enqueue_task(task, db_session)

        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.status == "Pending"
        assert event.task_id == str(task.task_id)

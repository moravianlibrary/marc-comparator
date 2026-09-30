"""A task's log is kept at both ends, and does not grow without limit.

It used to. The column was rewritten whole on every flush, so a task that
logged N times wrote O(N²) bytes and left every earlier copy dead behind it.
Measured on the local cluster before this changed: 36 task rows holding 20 MB
of text occupied 215 MB of TOAST, and one log had reached 7.5 MB.
"""

import logging
from types import SimpleNamespace

import pytest

from adapters.tasks import TRACEBACK_HEAD_CHARS, TRACEBACK_TAIL_CHARS, TaskHandler


class _Session:
    def __init__(self):
        self.flushes = 0

    def flush(self):
        self.flushes += 1

    def rollback(self):  # pragma: no cover - only on a failed flush
        pass


def _handler(existing: str | None = None) -> tuple[TaskHandler, SimpleNamespace, _Session]:
    task = SimpleNamespace(traceback=existing, severity=None)
    session = _Session()
    handler = TaskHandler(session, task, SimpleNamespace())  # type: ignore[arg-type]
    handler.setFormatter(logging.Formatter("%(message)s"))
    return handler, task, session


def _log(handler: TaskHandler, message: str, level: int = logging.INFO) -> None:
    handler.emit(logging.LogRecord("t", level, __file__, 1, message, None, None))


class TestTheLogIsBounded:
    def test_a_short_log_is_kept_whole(self):
        handler, task, _ = _handler()

        for i in range(5):
            _log(handler, f"line {i}")
        handler.flush()

        assert task.traceback is not None
        for i in range(5):
            assert f"line {i}" in task.traceback

    def test_a_long_log_stops_growing(self):
        handler, task, _ = _handler()

        for i in range(200_000):
            _log(handler, f"Processed {i} records so far.")
        handler.flush()

        assert task.traceback is not None
        assert len(task.traceback) <= TRACEBACK_HEAD_CHARS + TRACEBACK_TAIL_CHARS + 200

    def test_both_ends_survive(self):
        handler, task, _ = _handler()

        _log(handler, "STARTING with settings X")
        for i in range(200_000):
            _log(handler, f"Processed {i} records so far.")
        _log(handler, "FINISHED after everything")
        handler.flush()

        assert task.traceback is not None
        assert "STARTING with settings X" in task.traceback
        assert "FINISHED after everything" in task.traceback

    def test_what_was_dropped_is_counted(self):
        handler, task, _ = _handler()

        for i in range(200_000):
            _log(handler, f"Processed {i} records so far.")
        handler.flush()

        assert task.traceback is not None
        assert "earlier lines dropped" in task.traceback

    def test_nothing_is_marked_dropped_when_nothing_was(self):
        handler, task, _ = _handler()

        _log(handler, "one line")
        handler.flush()

        assert task.traceback is not None
        assert "dropped" not in task.traceback


class TestWhatThePreviousAttemptWrote:
    def test_it_is_kept(self):
        # "It failed the same way three times" is only visible if the earlier
        # attempts' logs survive the retry.
        handler, task, _ = _handler(existing="[attempt 1] it went wrong\n")

        _log(handler, "attempt 2 starting")
        handler.flush()

        assert task.traceback is not None
        assert "[attempt 1] it went wrong" in task.traceback
        assert "attempt 2 starting" in task.traceback


class TestFlushing:
    def test_a_routine_run_flushes_on_the_interval(self):
        handler, _, session = _handler()

        for i in range(TaskHandler.FLUSH_INTERVAL * 3):
            _log(handler, f"line {i}")

        assert session.flushes == 3

    def test_something_worth_seeing_is_written_at_once(self):
        handler, task, session = _handler()

        _log(handler, "quiet")
        assert session.flushes == 0

        _log(handler, "it broke", level=logging.ERROR)

        assert session.flushes == 1
        assert task.traceback is not None
        assert "it broke" in task.traceback

    @pytest.mark.parametrize("level", [logging.WARNING, logging.ERROR, logging.CRITICAL])
    def test_every_escalation_is_written_at_once(self, level):
        handler, _, session = _handler()

        _log(handler, "something", level=level)

        assert session.flushes == 1

"""Attributes every SQL statement to the application code that issued it.

The two profilers already wired up here each answer half a question.
``pg_stat_statements`` says what SQL a run executed and how long the server
spent on it. py-spy says where the process's wall clock went. Neither says
which line of Python asked for fifty thousand queries, and on this workload
that has repeatedly been the thing worth knowing: the statements are cheap
individually, the server is busy for a few percent of the run, and the cost is
the *number* of round trips rather than the price of any one of them. A query
issued from a loop is invisible to the first instrument, which sees one entry
with a large ``calls``, and easy to miss in the second, which samples a stack
that is only briefly inside the driver.

This listener records, per (statement, call site), how many times it ran and
how long it took, with the whole application stack that led to it. It is off
unless ``SQL_TRACE_ENABLED`` is set: capturing a stack per query costs real
time, and an instrument that changes what it measures is worth carrying only
while you are looking at it.

Counters are cumulative for the life of the process and are dumped as JSON on
a timer. Nothing resets them — a measurement of one stage is the difference
between two dumps, which is also the only way to measure a stage of a worker
that is running other things.
"""

from __future__ import annotations

import atexit
import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import config

#: Frames outside this tree are dropped from the captured stack. The point of
#: the capture is the application's own call path; SQLAlchemy's and Celery's
#: internals are the same twenty frames every time and only bury it.
_APP_ROOT = str(Path(__file__).resolve().parent.parent)

#: ...and these are dropped from inside it. The virtualenv sits *under* the
#: application root, so the root test alone admits every library frame — which
#: is precisely what this capture exists to leave out.
_NOT_APP = ("/site-packages/", "/.venv/", "/adapters/sql_tracing.py")

#: Set once install() has run, so a second call (a re-imported module, a test)
#: does not register the listeners twice and double every count.
_installed = False


@dataclass
class _CallSite:
    """One (statement, stack) pair and what it has cost so far."""

    sql: str
    stack: tuple[str, ...]
    count: int = 0
    total_ns: int = 0

    def as_json(self) -> dict:
        return {
            "sql": self.sql,
            "stack": list(self.stack),
            "count": self.count,
            "total_ms": round(self.total_ns / 1_000_000, 3),
        }


@dataclass
class _Totals:
    """Everything this process has recorded, keyed by (sql, stack)."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    sites: dict[tuple[str, tuple[str, ...]], _CallSite] = field(default_factory=dict)
    statements: int = 0
    total_ns: int = 0


_totals = _Totals()


def _normalise(statement: str) -> str:
    """Collapse a statement to a comparable, loggable one-liner.

    Parameters are already out of the text — SQLAlchemy passes them separately
    — so the only noise is the formatting SQLAlchemy emits for readability.
    """

    collapsed = " ".join(statement.split())
    limit = config.sql_trace.max_sql_length
    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "…"


def _capture_stack() -> tuple[str, ...]:
    """The application frames on the stack, innermost first.

    Walks the frames directly rather than going through ``traceback``: this
    runs once per statement, and building formatted FrameSummary objects for
    the thirty-odd library frames that are then thrown away costs more than
    the query being measured on the short ones.
    """

    frames: list[str] = []
    limit = config.sql_trace.max_frames
    frame = sys._getframe(1)
    while frame is not None and len(frames) < limit:
        code = frame.f_code
        filename = code.co_filename
        # Raw string tests rather than Path(): this runs once per statement,
        # and building a Path per frame costs more than the short queries do.
        if filename.startswith(_APP_ROOT) and not any(part in filename for part in _NOT_APP):
            relative = filename[len(_APP_ROOT) + 1 :]
            frames.append(f"{relative}:{frame.f_lineno} {code.co_name}")
        frame = frame.f_back
    return tuple(frames)


def _record(statement: str, elapsed_ns: int, stack: tuple[str, ...]) -> None:
    sql = _normalise(statement)
    key = (sql, stack)
    with _totals.lock:
        site = _totals.sites.get(key)
        if site is None:
            site = _CallSite(sql=sql, stack=stack)
            _totals.sites[key] = site
        site.count += 1
        site.total_ns += elapsed_ns
        _totals.statements += 1
        _totals.total_ns += elapsed_ns


def snapshot() -> dict:
    """A consistent view of the counters, safe to serialise."""

    with _totals.lock:
        sites = [site.as_json() for site in _totals.sites.values()]
        statements = _totals.statements
        total_ns = _totals.total_ns
    sites.sort(key=lambda entry: entry["total_ms"], reverse=True)
    return {
        "pid": os.getpid(),
        "captured_at": time.time(),
        "statements": statements,
        "total_ms": round(total_ns / 1_000_000, 3),
        "sites": sites,
    }


def dump() -> Path | None:
    """Write this process's counters to its own file under the output dir.

    One file per process: the worker is a prefork pool, every child traces
    independently, and merging them here would need shared memory to do what
    the reader can do trivially by summing the files.
    """

    directory = Path(config.sql_trace.output_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    target = directory / f"{os.getpid()}.json"
    # Written beside the target and moved, so a reader never sees half a file.
    staging = target.with_suffix(".json.part")
    try:
        staging.write_text(json.dumps(snapshot()))
        staging.replace(target)
    except OSError:
        return None
    return target


def _dump_loop() -> None:
    interval = config.sql_trace.dump_seconds
    while True:
        time.sleep(interval)
        dump()


def install() -> None:
    """Start tracing, if it is switched on. Safe to call more than once."""

    global _installed
    if _installed or not config.sql_trace.enabled:
        return
    _installed = True

    @event.listens_for(Engine, "before_cursor_execute")
    def _before(_conn, _cursor, _statement, _parameters, context, _executemany):
        context._sql_trace_started = time.perf_counter_ns()

    @event.listens_for(Engine, "after_cursor_execute")
    def _after(_conn, _cursor, statement, _parameters, context, _executemany):
        started = getattr(context, "_sql_trace_started", None)
        if started is None:
            return
        _record(statement, time.perf_counter_ns() - started, _capture_stack())

    threading.Thread(target=_dump_loop, daemon=True, name="sql-trace-dump").start()
    # A dump on the way out, so a short-lived process still reports.
    atexit.register(dump)

import logging
from collections import deque
from collections.abc import Callable
from contextlib import AbstractContextManager as ContextManager
from typing import Any

from celery import Celery, shared_task
from celery import Task as CeleryTask
from celery.signals import worker_process_init
from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.database import DatabaseSession, get_db_session
from adapters.events import TaskProgressEvent, TaskStatusEvent, publish_event
from adapters.lock_server import one_at_a_time_lock
from config import config

# Importing entities to register with the ORM
from entities.catalog_record import CatalogRecord  # noqa: F401
from entities.marc_sector import MarcRecordIndex, MarcSector  # noqa: F401
from entities.report_artifact import ReportArtifact  # noqa: F401
from entities.role import Role  # noqa: F401
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskSeverity, TaskStatus, TaskType
from entities.user import User  # noqa: F401
from settings.models import CatalogSettings
from tasks.models import TaskSettings  # noqa: F401

ANALYTICS_REBUILD_TASK_TYPES = {
    TaskType.SyncRecords,
    TaskType.FetchBatchOfRecords,
    TaskType.ProcessRecords,
    TaskType.ValidateRecords,
    TaskType.LinkRecordsToAuthorities,
    TaskType.CompareRecords,
}

#: Max times a task may be (re)delivered before it is treated as a poison
#: message and failed outright, instead of crash-looping the worker forever.
MAX_TASK_ATTEMPTS = 3

#: Redis redelivers an in-flight task after this many seconds even if the
#: original is still running. Must exceed the longest legitimate task (a full
#: base sync); the orphaned-task reaper covers anything that outlives it.
TASK_VISIBILITY_TIMEOUT = 6 * 60 * 60  # 6 hours

#: A Started task whose heartbeat is older than this (and which is not in any
#: worker's active set) is treated as orphaned and failed by the reaper. Must
#: exceed the longest legitimate gap between progress writes.
REAPER_HEARTBEAT_TIMEOUT = 15 * 60  # 15 minutes

tasks_client = Celery(
    "tasks",
    broker=config.broker.url,
    broker_connection_retry_on_startup=True,
    result_backend=f"db+{config.postgres.url}",
    timezone=config.timezone,
)

tasks_client.conf.redbeat_redis_url = config.broker.url

# --- Redelivery safety (see docs / PLAN Workstream 1) ---
# Ack a task only after it finishes so a worker death (even SIGKILL) redelivers
# it instead of dropping it. prefetch_multiplier=1 reserves only what is actively
# running, shrinking the lost-on-crash window and stopping queue hoarding.
tasks_client.conf.task_acks_late = True
tasks_client.conf.task_reject_on_worker_lost = True
tasks_client.conf.worker_prefetch_multiplier = 1
tasks_client.conf.broker_transport_options = {
    "visibility_timeout": TASK_VISIBILITY_TIMEOUT,
}


class TaskAlreadyRunningError(Exception):
    """Raised when a task's run-lock is already held by a live copy.

    Happens when a task is redelivered while the original is still running
    (i.e. it outlived the visibility timeout). The duplicate must abort
    WITHOUT touching the task row — the original owns it.
    """

    def __init__(self, task_id: str):
        super().__init__(f"Task '{task_id}' is already running; skipping duplicate")


class TaskRevokedError(Exception):
    """Raised when a message arrives for a task that has already been revoked.

    ``control.revoke`` reaches the workers that are listening when it is sent,
    and each keeps the id in memory. A message redelivered after that worker
    restarted — which ``acks_late`` guarantees will happen if it was killed
    mid-task — arrives at a worker that never heard the revoke. The row is the
    durable record of the decision, so the row is what decides.
    """

    def __init__(self, task_id: str):
        super().__init__(f"Task '{task_id}' was revoked; not running it")


class PoisonPillError(Exception):
    """Raised when a task has been redelivered more than MAX_TASK_ATTEMPTS times.

    The row is marked Failure before this is raised; raising it lets Celery ack
    the message (acks_late acks on completion, success or failure) so the
    crash-loop is broken.
    """

    def __init__(self, task_id: str, attempts: int):
        super().__init__(
            f"Task '{task_id}' exceeded {MAX_TASK_ATTEMPTS} attempts "
            f"({attempts}); marking as failed (poison message)"
        )


@worker_process_init.connect
def _reset_db_pool(**_kwargs):
    """Drop pooled DB connections inherited from the prefork parent.

    Forked workers would otherwise share the parent's sockets, which
    corrupts the protocol (SSL EOF / bad record mac errors). dispose with
    close=False discards the pool without closing the parent's FDs.
    """
    from adapters.database import engine

    engine.dispose(close=False)


@worker_process_init.connect
def _install_sql_tracing(**_kwargs):
    """Start per-call-site SQL accounting in each pool child, if enabled.

    Installed per child rather than once in the parent: the listeners would
    survive the fork, but the counters and the dump thread would not — a
    thread does not cross fork(), so the parent's dumper is gone in the child
    and nothing would ever be written.
    """
    from adapters.sql_tracing import install

    install()


type TasksClient = Celery

LEVEL_NO_TO_SEVERITY = {
    logging.INFO: TaskSeverity.Info,
    logging.WARNING: TaskSeverity.Warning,
    logging.ERROR: TaskSeverity.Error,
    logging.CRITICAL: TaskSeverity.Critical,
}


#: How much of a task's log is kept, in characters, at each end.
#:
#: The log used to grow without limit, and the column was rewritten whole on
#: every flush — so a task that logged N times wrote O(N²) bytes, each version
#: leaving the previous one dead. Measured on the local cluster: 36 task rows
#: holding 20 MB of text occupied **215 MB of TOAST**, and one task's log had
#: reached 7.5 MB on its own.
#:
#: Both ends are kept because both are read. The head is what the task set out
#: to do and what it complained about early; the tail is what it was doing
#: when it stopped, which is the first thing anyone looks at. The middle of a
#: long run is mostly "Processed N records so far", and what is dropped is
#: counted and said so.
#:
#: 64 KB in total is roughly 800 lines. Of the 35 logs on the local cluster,
#: 22 are already smaller than that and would be kept whole.
TRACEBACK_HEAD_CHARS = 32 * 1024
TRACEBACK_TAIL_CHARS = 32 * 1024

#: Marker written where the middle was dropped. Takes the count, so a reader
#: can tell a log that was trimmed from one that simply ended.
TRACEBACK_ELISION = "\n[... {count} earlier lines dropped ...]\n\n"


class TaskHandler(logging.Handler):
    """
    Logging handler that writes messages to a Task.traceback field.
    Batches flushes to reduce DB overhead — flushes every `FLUSH_INTERVAL`
    entries, on severity escalation, and on close.

    What it stores is bounded; see ``TRACEBACK_HEAD_CHARS``. The handler keeps
    the composed value rather than appending to the column, because appending
    is what made the writes quadratic.
    """

    #: Entries between routine flushes. Liveness for a running task comes from
    #: the progress event and `Task.progress`, not from this, so the log does
    #: not need writing as often as it is written to — and each write is a
    #: fresh copy of the whole column. Anything that raises the severity still
    #: flushes at once, because that is what somebody is waiting to see.
    FLUSH_INTERVAL = 50

    def __init__(self, db: Session, task: Task, managed_task: "ManagedTask", level=logging.DEBUG):
        super().__init__(level)
        self.db_session = db
        self.task = task
        self._managed_task = managed_task
        self.current_level = logging.INFO
        self._pending = 0
        self._buffer: list[str] = []

        self._head: list[str] = []
        self._head_chars = 0
        self._tail: deque[str] = deque()
        self._tail_chars = 0
        self._dropped = 0

        # A retried task keeps what its earlier attempt wrote, which is what
        # makes "it failed the same way three times" visible.
        if task.traceback:
            self._keep(task.traceback)

    def _keep(self, entry: str) -> None:
        """Take one entry into the bounded log, dropping the oldest middle."""

        if self._head_chars < TRACEBACK_HEAD_CHARS:
            self._head.append(entry)
            self._head_chars += len(entry)
            return

        self._tail.append(entry)
        self._tail_chars += len(entry)
        while self._tail_chars > TRACEBACK_TAIL_CHARS and len(self._tail) > 1:
            self._tail_chars -= len(self._tail.popleft())
            self._dropped += 1

    def _compose(self) -> str:
        head = "".join(self._head)
        if not self._tail:
            return head
        if not self._dropped:
            return head + "".join(self._tail)
        return head + TRACEBACK_ELISION.format(count=self._dropped) + "".join(self._tail)

    def _flush_traceback(self):
        if self._buffer:
            for entry in self._buffer:
                self._keep(entry)
            self._buffer.clear()
            # Assigned, not appended: the value is already the whole log, and
            # appending to the column is what grew it without limit.
            self.task.traceback = self._compose()
        try:
            self.db_session.flush()
        except Exception:
            self.db_session.rollback()
        self._pending = 0

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        timestamp = config.timestamp
        entry = f"[{timestamp}] {record.levelname}: {msg}\n"

        self._buffer.append(entry)

        self._pending += 1
        severity_changed = False

        if record.levelno > self.current_level:
            self.current_level = record.levelno

            severity = LEVEL_NO_TO_SEVERITY.get(record.levelno)
            if severity:
                self.task.severity = severity
                severity_changed = True

        if severity_changed or self._pending >= self.FLUSH_INTERVAL:
            self._flush_traceback()

    def flush(self):
        """Persist whatever is still buffered onto the task row."""
        if self._buffer:
            self._flush_traceback()

    def close(self):
        self.flush()
        super().close()


class ManagedTask:
    """
    Context manager for managing task execution. Handles database
    session, task loading, logging, and optional locking.

    Parameters
    ----------
    task_id : str
        The ID of the task to manage.
    lock_key : str | None = None
        The key for the distributed lock. If provided, a lock will be
        acquired when entering the context.
    lock_blocking_timeout : int = 0
        The timeout in seconds for acquiring the lock.
    """

    def __init__(
        self,
        task_id: str,
        lock_key: str | None = None,
        lock_blocking_timeout: int = 0,
    ):
        self.task_id = task_id

        self.lock_key = lock_key
        self.lock_blocking_timeout = lock_blocking_timeout
        self.lock: ContextManager | None = None
        self._lock_obj = None

        # Model defaults until __aenter__ loads the stored settings.
        self.task_settings: TaskSettings = TaskSettings()

        # Populated by __aenter__. Exposed through properties that raise rather than
        # returning None, so the ~80 use sites below are not each an optional access —
        # using a ManagedTask outside its context is a bug, not a case to handle.
        self._db_session: DatabaseSession | None = None
        self._task: Task | None = None
        self._logger: logging.Logger | None = None

        self._total: int | None = None
        self.progress: int = 0
        self.before_commit: Callable[[], None] | None = None
        self._handler: TaskHandler | None = None

    @property
    def db_session(self) -> DatabaseSession:
        if self._db_session is None:
            raise RuntimeError(
                f"ManagedTask({self.task_id}) used outside its async context: no DB session"
            )

        return self._db_session

    @db_session.setter
    def db_session(self, value: DatabaseSession) -> None:
        self._db_session = value

    @property
    def task(self) -> Task:
        if self._task is None:
            raise RuntimeError(
                f"ManagedTask({self.task_id}) used outside its async context: task not loaded"
            )

        return self._task

    @task.setter
    def task(self, value: Task) -> None:
        self._task = value

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            raise RuntimeError(
                f"ManagedTask({self.task_id}) used outside its async context: no logger"
            )

        return self._logger

    @logger.setter
    def logger(self, value: logging.Logger) -> None:
        self._logger = value

    @property
    def total(self) -> int | None:
        return self._total

    @total.setter
    def total(self, value: int | None) -> None:
        self._total = value
        # Checks the backing field, not the property: before __aenter__ this is a
        # legitimate "not loaded yet", where the property would raise.
        if value is not None and self._task is not None:
            self.update_progress()

    def save_task(self):
        self.task.save(self.db_session, commit=False)

    def update_progress(self) -> None:
        self.task.progress = self.progress / self._total if self._total else None
        # Liveness heartbeat for the orphaned-task reaper (see reap_orphaned_tasks).
        self.task.heartbeat = config.timestamp
        self.save_task()
        publish_event(
            TaskProgressEvent(
                task_id=str(self.task.task_id),
                progress=self.task.progress,
                created_by=str(self.task.created_by),
            )
        )

    def cycle_session(self) -> None:
        """Close the current DB session and open a fresh one.

        Commits pending work (with before_commit if set), closes the old
        session, opens a new one, and re-loads the task entity. Updates
        all internal references (handler, db_session, task).
        """
        if self.before_commit:
            self.before_commit()
        self.db_session.commit()

        task_id = self.task.task_id

        self.db_session.close()

        self.db_session = get_db_session()
        reloaded = self.db_session.get(Task, task_id)
        if reloaded is None:
            raise RuntimeError(f"Task {task_id} disappeared while cycling the DB session")

        self.task = reloaded

        if self._handler:
            self._handler.db_session = self.db_session
            self._handler.task = self.task

    def _release_lock(self) -> None:
        if self.lock:
            try:
                self.lock.__exit__(None, None, None)
            except Exception:
                logging.warning("Failed to release task lock", exc_info=True)
            self.lock = None
            self._lock_obj = None

    def _publish_status(self) -> None:
        publish_event(
            TaskStatusEvent(
                task_id=str(self.task.task_id),
                task_type=self.task.type.value,
                target=self.task.target,
                name=self.task.name,
                status=self.task.status.value,
                severity=self.task.severity.value,
                created_by=str(self.task.created_by),
            )
        )

    async def __aenter__(self) -> "ManagedTask":
        # --- DB session ---
        self.db_session = get_db_session()

        # --- Load task ---
        self.task = Task.get(self.db_session, self.task_id)

        # --- Acquire lock FIRST (before touching the row) ---
        # A redelivered duplicate (task that outlived the visibility timeout)
        # must bail without altering the row the original owns. If the lock
        # server is unreachable, degrade gracefully and run without the guard
        # rather than failing the task outright (per-record writes are
        # idempotent for sequential re-runs; the guard only matters for the
        # rare simultaneous-redelivery case).
        if self.lock_key:
            self.lock = one_at_a_time_lock(
                self.lock_key, blocking_timeout=self.lock_blocking_timeout
            )
            try:
                lock_obj = self.lock.__enter__()
            except Exception:
                logging.warning(
                    f"Lock server unavailable for '{self.lock_key}'; proceeding without run-lock",
                    exc_info=True,
                )
                self.lock = None
            else:
                if not lock_obj:
                    self._release_lock()
                    self.db_session.close()
                    raise TaskAlreadyRunningError(self.task_id)
                self._lock_obj = lock_obj

        # Checked before the row is touched: marking it Started here is what
        # would hide the revoke from the guard at the other end, which only
        # sees the status after the work has already been done.
        if self.task.status == TaskStatus.Revoked:
            self._release_lock()
            self.db_session.close()
            raise TaskRevokedError(self.task_id)

        try:
            # --- Poison-message guard ---
            # Bound redeliveries under acks_late so a task that reliably crashes
            # the worker fails instead of crash-looping forever.
            self.task.attempts = (self.task.attempts or 0) + 1
            self.save_task()
            self.db_session.commit()
            if self.task.attempts > MAX_TASK_ATTEMPTS:
                self.task.status = TaskStatus.Failure
                self.task.severity = TaskSeverity.Error
                self.task.finished_at = config.timestamp
                if self.task.traceback:
                    self.task.traceback += "\nPoison message: exceeded max redeliveries\n"
                else:
                    self.task.traceback = "Poison message: exceeded max redeliveries\n"
                self.save_task()
                self.db_session.commit()
                self._publish_status()
                raise PoisonPillError(self.task_id, self.task.attempts)

            # --- Logger ---
            self.logger = logging.getLogger(f"task-{self.task_id}")
            handler = TaskHandler(self.db_session, self.task, self)
            self._handler = handler
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

            # --- Load task settings ---
            self.task_settings = (
                Settings.get(self.db_session, SettingsScope.Tasks, TaskSettings) or TaskSettings()
            )

            # --- Initialize Aleph client registry from config ---
            catalog_settings: CatalogSettings | None = Settings.get(
                self.db_session, SettingsScope.Catalog, CatalogSettings
            )
            if catalog_settings:
                from adapters.aleph_client_registry import AlephClientRegistry

                AlephClientRegistry.load_from_settings(catalog_settings)

            # --- Mark task as started ---
            self.logger.info("Task started")
            self.task.status = TaskStatus.Started
            self.task.started_at = config.timestamp
            self.task.heartbeat = config.timestamp
            self.save_task()
            self.db_session.commit()
            self._publish_status()

            return self
        except PoisonPillError:
            # Row already marked Failure above; just release resources.
            self._release_lock()
            self.db_session.close()
            raise
        except Exception:
            # Genuine setup error: mark the row Failure so it is not left
            # wedged in Started, then release resources.
            try:
                self.task.status = TaskStatus.Failure
                self.task.severity = TaskSeverity.Error
                self.task.finished_at = config.timestamp
                self.save_task()
                self.db_session.commit()
                self._publish_status()
            except Exception:
                self.db_session.rollback()
            self._release_lock()
            self.db_session.close()
            raise

    async def __aexit__(self, exc_type, exc_value, traceback):
        # --- Set final task status ---
        try:
            # Cancellation is committed by a different session while a worker
            # owns this task's logging/progress session. Do not let its stale
            # identity-map row overwrite Revoked during finalisation.
            with self.db_session.no_autoflush:
                current_status = self.db_session.execute(
                    select(Task.status).where(Task.task_id == self.task.task_id)
                ).scalar_one_or_none()
            if current_status == TaskStatus.Revoked:
                self.db_session.rollback()
                return False

            if exc_type is None:
                self.task.status = TaskStatus.Success
                self.task.progress = 1.0
                self.logger.info("Task completed successfully")
            else:
                self.task.status = TaskStatus.Failure
                self.logger.error(f"Task failed with exception: {exc_value}", exc_info=True)
            self.task.finished_at = config.timestamp
            self.save_task()

            # Rebuild analytics after successful data-changing tasks
            if exc_type is None and self.task.type in ANALYTICS_REBUILD_TASK_TYPES:
                try:
                    from catalog_records.analytics import rebuild_all

                    rebuild_all(self.db_session)
                except Exception as e:
                    logging.warning(f"Analytics rebuild failed: {e}")

            # The handler only writes to the row every FLUSH_INTERVAL entries,
            # so without this the tail of every traceback — the final status
            # line, and the exception on a failure — is dropped.
            if self._handler:
                self._handler.flush()

            if self.before_commit:
                self.before_commit()
            self.db_session.commit()

            # Publish events AFTER commit so clients refetch committed data
            publish_event(
                TaskProgressEvent(
                    task_id=str(self.task.task_id),
                    progress=self.task.progress,
                    created_by=str(self.task.created_by),
                )
            )
            publish_event(
                TaskStatusEvent(
                    task_id=str(self.task.task_id),
                    task_type=self.task.type.value,
                    target=self.task.target,
                    name=self.task.name,
                    status=self.task.status.value,
                    severity=self.task.severity.value,
                    created_by=str(self.task.created_by),
                )
            )
        finally:
            # --- Release resources ---
            # `logging.getLogger(f"task-{id}")` is cached process-wide, so an
            # attached handler outlives the run and would keep writing through
            # a closed session if the same task id is retried on this worker.
            if self._handler:
                if self._logger:
                    self._logger.removeHandler(self._handler)
                try:
                    self._handler.close()
                except Exception:
                    logging.warning("Failed to close task log handler", exc_info=True)
                self._handler = None

            if self.lock:
                self.lock.__exit__(None, None, None)

            if self.db_session:
                self.db_session.close()


def handle_batch_progress_snippet(ctx: ManagedTask) -> None:
    """Increment progress and periodically report/persist progress."""
    ctx.progress += 1

    # Progress reporting: WS event + traceback log (no commit)
    if ctx.progress % ctx.task_settings.progress_update_interval == 0:
        ctx.logger.info(f"Processed {ctx.progress} records so far.")
        ctx.update_progress()

    # DB commit + session cycle for regular tasks (no SectorBuffer)
    if ctx.before_commit is None and ctx.progress % ctx.task_settings.commit_interval == 0:
        ctx.cycle_session()

    # Sector flush + DB commit + session cycle for record-writing tasks
    if (
        ctx.before_commit is not None
        and ctx.progress % ctx.task_settings.sector_flush_interval == 0
    ):
        ctx.cycle_session()

    # Periodically rebuild analytics + facet cube for live dashboard updates
    interval = ctx.task_settings.analytics_rebuild_interval
    if (
        interval > 0
        and ctx.task.type in ANALYTICS_REBUILD_TASK_TYPES
        and ctx.progress % interval == 0
    ):
        _rebuild_analytics(ctx)


def _rebuild_analytics(ctx: ManagedTask) -> None:
    """Rebuild analytics table and facet cube. Swallows errors to avoid killing the task."""
    try:
        from catalog_records.analytics import rebuild_all

        rebuild_all(ctx.db_session)
    except Exception as e:
        ctx.logger.warning(f"Mid-task analytics rebuild failed: {e}")


def handle_final_batch_snippet(ctx: ManagedTask) -> None:
    """Commit any remaining DB changes and update task progress."""
    ctx.cycle_session()
    ctx.update_progress()


"""
Celery cannot directly run async tasks, so we use asgiref to bridge
the gap.

Importing inside the function to provide separation between
app and worker environments.
"""


@shared_task(name="fetch_record_task", bind=True)
def fetch_record_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from catalog_records.tasks import fetch_record_task

    return async_to_sync(fetch_record_task)(str(self.request.id))


@shared_task(name="fetch_batch_records_task", bind=True)
def fetch_batch_of_records_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from catalog_records.tasks import fetch_batch_of_records_task

    return async_to_sync(fetch_batch_of_records_task)(str(self.request.id))


@shared_task(bind=True, name="catalog_sync_task")
def records_sync_task(self: CeleryTask, lock_key: str, lock_blocking_timeout: int):
    from asgiref.sync import async_to_sync

    from catalog_records.tasks import records_sync_task

    return async_to_sync(records_sync_task)(str(self.request.id), lock_key, lock_blocking_timeout)


@shared_task(name="validate_records", bind=True)
def validate_records_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from validation.tasks import validate_records

    return async_to_sync(validate_records)(str(self.request.id))


@shared_task(name="link_records_to_authorities", bind=True)
def link_records_to_authorities(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from authority_linking.tasks import authority_linking

    return async_to_sync(authority_linking)(str(self.request.id))


@shared_task(name="compare_records", bind=True)
def compare_records_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from comparison.tasks import compare_records

    return async_to_sync(compare_records)(str(self.request.id))


@shared_task(name="process_records_task", bind=True)
def process_records_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from catalog_records.tasks import process_records

    return async_to_sync(process_records)(str(self.request.id))


@shared_task(name="delete_tasks_task", bind=True)
def delete_tasks_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from tasks.tasks import delete_tasks

    return async_to_sync(delete_tasks)(str(self.request.id))


@shared_task(name="refresh_analytics_task", bind=True)
def refresh_analytics_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from maintenance.tasks import refresh_analytics

    return async_to_sync(refresh_analytics)(str(self.request.id))


@shared_task(name="cleanup_stale_locks_task", bind=True)
def cleanup_stale_locks_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from maintenance.tasks import cleanup_stale_locks

    return async_to_sync(cleanup_stale_locks)(str(self.request.id))


@shared_task(name="compact_sectors_task", bind=True)
def compact_sectors_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from maintenance.tasks import compact_sectors

    return async_to_sync(compact_sectors)(str(self.request.id))


@shared_task(name="create_report_task", bind=True)
def create_report_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from reports.tasks import create_report

    return async_to_sync(create_report)(str(self.request.id))


@shared_task(name="rebuild_search_vectors_task", bind=True)
def rebuild_search_vectors_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from maintenance.tasks import rebuild_search_vectors

    return async_to_sync(rebuild_search_vectors)(str(self.request.id))


@shared_task(name="rescore_comparisons_task", bind=True)
def rescore_comparisons_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from maintenance.tasks import rescore_comparisons

    return async_to_sync(rescore_comparisons)(str(self.request.id))


@shared_task(name="harvest_plugin_task", bind=True)
def harvest_plugin_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from harvest.tasks import harvest_plugin

    return async_to_sync(harvest_plugin)(str(self.request.id))


@shared_task(name="periodic_task_cleanup")
def periodic_task_cleanup(max_age_days: int = 30) -> None:
    """Called by redbeat. Creates a Task DB row and dispatches delete_tasks."""
    from adapters.database import SessionLocal
    from entities.task import Task, TaskType
    from entities.user import SYSTEM_USER_ID

    db = SessionLocal()
    try:
        task = Task(
            name=f"Periodic task cleanup (>{max_age_days} days)",
            type=TaskType.DeleteTasks,
            data={"max_age_days": max_age_days},
            created_by=SYSTEM_USER_ID,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        dispatch_task(task)
    finally:
        db.close()


@shared_task(name="periodic_sector_compaction")
def periodic_sector_compaction() -> None:
    """Called by redbeat. Creates a Task DB row and dispatches compact_sectors."""
    from adapters.database import SessionLocal
    from entities.task import Task, TaskType
    from entities.user import SYSTEM_USER_ID

    db = SessionLocal()
    try:
        task = Task(
            name="Periodic sector compaction",
            type=TaskType.CompactSectors,
            created_by=SYSTEM_USER_ID,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        dispatch_task(task)
    finally:
        db.close()


@shared_task(name="periodic_sync_records")
def periodic_sync_records(base: str) -> None:
    """Called by redbeat. Builds an incremental SyncRecords task for a base.

    from_date is derived from the base's newest ``latest_sync`` so each run
    harvests only what changed since the last successful sync (full harvest on
    the first run, when there are no records yet).
    """
    from sqlalchemy import func as sa_func

    from adapters.database import SessionLocal
    from catalog_records.models import SyncRecordsData
    from entities.user import SYSTEM_USER_ID

    db = SessionLocal()
    try:
        latest_sync = (
            db.query(sa_func.max(CatalogRecord.latest_sync))
            .filter(CatalogRecord.base == base)
            .scalar()
        )
        data = SyncRecordsData(base=base, from_date=latest_sync)
        task = Task(
            name=f"Scheduled sync for base {base}",
            type=TaskType.SyncRecords,
            data=data.model_dump(mode="json"),
            created_by=SYSTEM_USER_ID,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        dispatch_task(task)
    finally:
        db.close()


@shared_task(name="periodic_process_records")
def periodic_process_records() -> None:
    """Called by redbeat. Processes records nothing has processed yet.

    A sync clears ``processed_at`` on every record it touches, so the filter
    picks up new and changed records alike and never reprocesses settled ones.
    """
    from adapters.database import SessionLocal
    from catalog_records.models import RecordFilter
    from entities.user import SYSTEM_USER_ID

    db = SessionLocal()
    try:
        # Processing a large backlog can easily outrun the interval. Stacking
        # runs would have them fight over the same records, so skip this tick
        # instead — the next one picks up whatever is still unprocessed.
        in_flight = (
            db.query(Task)
            .filter(
                Task.type == TaskType.ProcessRecords,
                Task.status.in_([TaskStatus.Pending, TaskStatus.Started]),
            )
            .first()
        )
        if in_flight is not None:
            logging.info(
                f"Skipping scheduled processing: task {in_flight.task_id} is already "
                f"{in_flight.status.value}"
            )
            return

        data = RecordFilter(processed=False)
        task = Task(
            name="Scheduled processing of unprocessed records",
            type=TaskType.ProcessRecords,
            data=data.model_dump(mode="json"),
            created_by=SYSTEM_USER_ID,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        dispatch_task(task)
    finally:
        db.close()


@shared_task(name="periodic_harvest_plugin")
def periodic_harvest_plugin(plugin_name: str) -> None:
    """Recheck this plugin's enabled preference, then enqueue its harvest."""
    from asgiref.sync import async_to_sync

    from adapters.database import SessionLocal
    from entities.user import SYSTEM_USER_ID
    from harvest.dispatch import enqueue_harvest, get_harvest_settings
    from harvest.registry import find_plugin

    db = SessionLocal()
    try:
        plugin = find_plugin(plugin_name)
        settings = get_harvest_settings(db)
        if plugin is None or not settings.plugins.get(plugin_name, None):
            logging.info("Skipping schedule for removed harvest plugin %r", plugin_name)
            return
        if not settings.plugins[plugin_name].enabled:
            logging.info("Skipping disabled scheduled harvest for plugin %r", plugin_name)
            return
        async_to_sync(enqueue_harvest)(
            plugin_name,
            str(SYSTEM_USER_ID),
            db,
            scheduled=True,
        )
    finally:
        db.close()


@shared_task(name="reap_orphaned_tasks")
def reap_orphaned_tasks() -> None:
    """Fail tasks left stuck in ``Started`` after their worker died.

    Under ``acks_late`` a redelivered task normally re-runs to completion, but a
    task that outlives the visibility timeout (or is otherwise non-resumable)
    can sit in ``Started`` forever. A row is reaped only if BOTH hold: its
    heartbeat is stale AND its id is absent from every worker's active set — so
    a transient slow batch is never reaped. Marks matches ``Failure`` (does not
    resume the work; redelivery/rerun handles resumption).
    """
    from datetime import timedelta

    from sqlalchemy import and_, or_

    from adapters.database import SessionLocal

    db = SessionLocal()
    try:
        cutoff = config.timestamp - timedelta(seconds=REAPER_HEARTBEAT_TIMEOUT)
        candidates = (
            db.query(Task)
            .filter(
                Task.status == TaskStatus.Started,
                or_(
                    Task.heartbeat < cutoff,
                    and_(Task.heartbeat.is_(None), Task.started_at < cutoff),
                ),
            )
            .all()
        )
        if not candidates:
            return

        # Ids currently executing on any worker (None => workers unreachable).
        active_ids: set[str] = set()
        active = tasks_client.control.inspect().active()
        if active:
            for entries in active.values():
                for entry in entries:
                    tid = entry.get("id")
                    if tid:
                        active_ids.add(str(tid))

        reaped = 0
        for task in candidates:
            if str(task.task_id) in active_ids:
                continue
            task.status = TaskStatus.Failure
            task.severity = TaskSeverity.Error
            task.finished_at = config.timestamp
            task.traceback = (task.traceback or "") + (
                "Interrupted — no heartbeat (worker died); reaped by orphan sweep\n"
            )
            reaped += 1
            publish_event(
                TaskStatusEvent(
                    task_id=str(task.task_id),
                    task_type=task.type.value,
                    target=task.target,
                    name=task.name,
                    status=task.status.value,
                    severity=task.severity.value,
                    created_by=str(task.created_by),
                )
            )

        if reaped:
            db.commit()
            logging.warning(f"Reaped {reaped} orphaned task(s) stuck in Started")
    finally:
        db.close()


# celery's @shared_task is untyped — it hands back a Proxy whose attributes
# resolve only at runtime, so the values here cannot be typed more precisely.
TASK_DISPATCH: dict[TaskType, Any] = {
    TaskType.FetchRecord: fetch_record_task,
    TaskType.FetchBatchOfRecords: fetch_batch_of_records_task,
    TaskType.SyncRecords: records_sync_task,
    TaskType.ValidateRecords: validate_records_task,
    TaskType.LinkRecordsToAuthorities: link_records_to_authorities,
    TaskType.CompareRecords: compare_records_task,
    TaskType.ProcessRecords: process_records_task,
    TaskType.DeleteTasks: delete_tasks_task,
    TaskType.RefreshAnalytics: refresh_analytics_task,
    TaskType.CleanupStaleLocks: cleanup_stale_locks_task,
    TaskType.CompactSectors: compact_sectors_task,
    TaskType.RebuildSearchVectors: rebuild_search_vectors_task,
    TaskType.RescoreComparisons: rescore_comparisons_task,
    TaskType.CreateReport: create_report_task,
    TaskType.HarvestPlugin: harvest_plugin_task,
}


def dispatch_task(task: Task) -> None:
    """Dispatch a task to Celery based on its type."""
    celery_task = TASK_DISPATCH.get(task.type)
    if celery_task is None:
        raise ValueError(f"Unknown task type: {task.type}")

    kwargs: dict = {"task_id": str(task.task_id)}
    if task.type == TaskType.SyncRecords:
        if not task.data or "base" not in task.data:
            raise ValueError(f"SyncRecords task {task.task_id} has no 'base' in its data")
        kwargs["args"] = [f"catalog_sync_{task.data['base']}", 1]

    celery_task.apply_async(**kwargs)


async def enqueue_task(task: Task, db_session: DatabaseSession) -> TaskSchema:
    """
    Enqueues a task for processing. Saves the task to the database
    and dispatches it to the Celery worker.
    """
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    try:
        dispatch_task(task)
    except Exception as e:
        task.status = TaskStatus.Failure
        task.finished_at = config.timestamp
        task.traceback = f"Failed to dispatch task to worker: {e}"
        db_session.commit()
        publish_event(
            TaskStatusEvent(
                task_id=str(task.task_id),
                task_type=task.type.value,
                target=task.target,
                name=task.name,
                status=task.status.value,
                severity=task.severity.value,
                created_by=str(task.created_by),
            )
        )
        raise

    publish_event(
        TaskStatusEvent(
            task_id=str(task.task_id),
            task_type=task.type.value,
            target=task.target,
            name=task.name,
            status=task.status.value,
            severity=task.severity.value,
            created_by=str(task.created_by),
        )
    )

    return TaskSchema.model_validate(task, from_attributes=True)


async def revoke_task(task: Task, db_session: DatabaseSession) -> TaskSchema:
    """
    Revokes a task if it is in a revocable state.
    """
    if task.status not in {TaskStatus.Started, TaskStatus.Pending}:
        raise ValueError(f"Task with status '{task.status}' cannot be revoked.")

    tasks_client.control.revoke(str(task.task_id), terminate=True, signal="SIGTERM")

    task.status = TaskStatus.Revoked
    task.finished_at = config.timestamp

    task.save(db_session)

    publish_event(
        TaskStatusEvent(
            task_id=str(task.task_id),
            task_type=task.type.value,
            target=task.target,
            name=task.name,
            status=task.status.value,
            severity=task.severity.value,
            created_by=str(task.created_by),
        )
    )

    return TaskSchema.model_validate(task, from_attributes=True)

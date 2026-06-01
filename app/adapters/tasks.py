import logging
from typing import Callable, ContextManager, List, Optional

from celery import Celery
from celery import Task as CeleryTask
from celery import shared_task
from sqlalchemy.orm import Session

from adapters.database import Base, DatabaseSession, get_db_session
from adapters.events import TaskProgressEvent, TaskStatusEvent, publish_event
from adapters.lock_server import one_at_a_time_lock
from config import config

# Importing entities to register with the ORM
from entities.catalog_record import CatalogRecord  # noqa: F401
from entities.marc_sector import MarcRecordIndex, MarcSector  # noqa: F401
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

tasks_client = Celery(
    "tasks",
    broker=config.broker.url,
    broker_connection_retry_on_startup=True,
    result_backend=f"db+{config.postgres.url}",
    timezone=config.timezone,
)

tasks_client.conf.redbeat_redis_url = config.broker.url

type TasksClient = Celery

LEVEL_NO_TO_SEVERITY = {
    logging.INFO: TaskSeverity.Info,
    logging.WARNING: TaskSeverity.Warning,
    logging.ERROR: TaskSeverity.Error,
    logging.CRITICAL: TaskSeverity.Critical,
}


class TaskHandler(logging.Handler):
    """
    Logging handler that writes messages to a Task.traceback field.
    Batches commits to reduce DB overhead — flushes every `flush_interval`
    entries, on severity escalation, and on close.
    """

    FLUSH_INTERVAL = 10

    def __init__(self, db: Session, task: Task, level=logging.DEBUG):
        super().__init__(level)
        self.db_session = db
        self.task = task
        self.current_level = logging.INFO
        self._pending = 0

    def _commit(self):
        try:
            self.db_session.commit()
        except Exception:
            self.db_session.rollback()
        self._pending = 0

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        timestamp = config.timestamp
        entry = f"[{timestamp}] {record.levelname}: {msg}\n"

        if self.task.traceback:
            self.task.traceback += entry
        else:
            self.task.traceback = entry

        self._pending += 1
        severity_changed = False

        if record.levelno > self.current_level:
            self.current_level = record.levelno

            severity = LEVEL_NO_TO_SEVERITY.get(record.levelno)
            if severity:
                self.task.severity = severity
                severity_changed = True

        if severity_changed or self._pending >= self.FLUSH_INTERVAL:
            self._commit()

    def close(self):
        if self._pending > 0:
            self._commit()
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
        lock_key: Optional[str] = None,
        lock_blocking_timeout: int = 0,
    ):
        self.task_id = task_id

        self.lock_key = lock_key
        self.lock_blocking_timeout = lock_blocking_timeout
        self.lock: Optional[ContextManager] = None
        self._lock_obj = None

        self.logger: logging.Logger | None = None
        self.db_session: DatabaseSession | None = None
        self.task: Task | None = None
        self.task_settings: TaskSettings | None = None

        self._total: int | None = None
        self.progress: int = 0
        self.before_commit: Callable[[], None] | None = None

    @property
    def total(self) -> int | None:
        return self._total

    @total.setter
    def total(self, value: int | None) -> None:
        self._total = value
        if value is not None and self.task:
            self.update_progress()

    def save_task(self):
        self.task.save(self.db_session)

    def update_progress(self) -> None:
        self.task.progress = (
            self.progress / self._total if self._total else None
        )
        self.save_task()
        publish_event(TaskProgressEvent(
            task_id=str(self.task.task_id),
            progress=self.task.progress,
            created_by=str(self.task.created_by),
        ))

    async def __aenter__(self) -> "ManagedTask":
        # --- DB session ---
        self.db_session = get_db_session()

        # --- Load task ---
        self.task = Task.get(self.db_session, self.task_id)

        try:
            # --- Logger ---
            self.logger = logging.getLogger(f"task-{self.task_id}")
            handler = TaskHandler(self.db_session, self.task)
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

            # --- Load task settings ---
            self.task_settings: TaskSettings = (
                Settings.get(
                    self.db_session, SettingsScope.Tasks, TaskSettings
                )
                or TaskSettings()
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
            self.save_task()
            publish_event(TaskStatusEvent(
                task_id=str(self.task.task_id),
                task_type=self.task.type.value,
                name=self.task.name,
                status=self.task.status.value,
                severity=self.task.severity.value,
                created_by=str(self.task.created_by),
            ))

            # --- Acquire lock if needed ---
            if self.lock_key:
                self.lock = one_at_a_time_lock(
                    self.lock_key, self.lock_blocking_timeout
                )
                lock_obj = self.lock.__enter__()
                if not lock_obj:
                    raise ValueError(
                        f"Task lock '{self.lock_key}' is already acquired"
                    )
                self._lock_obj = lock_obj

            return self
        except Exception:
            await self.__aexit__(None, None, None)
            raise

    async def __aexit__(self, exc_type, exc_value, traceback):
        # --- Set final task status ---
        try:
            if exc_type is None:
                self.task.status = TaskStatus.Success
                self.logger.info("Task completed successfully")
            else:
                self.task.status = TaskStatus.Failure
                self.logger.error(
                    f"Task failed with exception: {exc_value}", exc_info=True
                )
            self.task.finished_at = config.timestamp
            self.save_task()
            publish_event(TaskStatusEvent(
                task_id=str(self.task.task_id),
                task_type=self.task.type.value,
                name=self.task.name,
                status=self.task.status.value,
                severity=self.task.severity.value,
                created_by=str(self.task.created_by),
            ))

            # Rebuild analytics after successful data-changing tasks
            if exc_type is None and self.task.type in ANALYTICS_REBUILD_TASK_TYPES:
                try:
                    from catalog_records.analytics import rebuild_all
                    rebuild_all(self.db_session)
                except Exception as e:
                    logging.warning(f"Analytics rebuild failed: {e}")
        finally:
            # --- Release resources ---
            if self.lock:
                self.lock.__exit__(None, None, None)

            if self.db_session:
                self.db_session.close()


def handle_batch_progress_snippet(ctx: ManagedTask) -> None:
    """Increment progress and periodically log + persist progress."""
    ctx.progress += 1

    if ctx.progress % ctx.task_settings.progress_update_interval == 0:
        ctx.logger.info(f"Processed {ctx.progress} records so far.")
        ctx.update_progress()

    # Periodically commit DB changes
    if ctx.progress % ctx.task_settings.commit_interval == 0:
        if ctx.before_commit:
            ctx.before_commit()
        ctx.db_session.commit()

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
    if ctx.before_commit:
        ctx.before_commit()
    ctx.db_session.commit()
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
def records_sync_task(
    self: CeleryTask, lock_key: str, lock_blocking_timeout: int
):
    from asgiref.sync import async_to_sync

    from catalog_records.tasks import records_sync_task

    return async_to_sync(records_sync_task)(
        str(self.request.id), lock_key, lock_blocking_timeout
    )


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


@shared_task(name="rebuild_search_vectors_task", bind=True)
def rebuild_search_vectors_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from maintenance.tasks import rebuild_search_vectors

    return async_to_sync(rebuild_search_vectors)(str(self.request.id))


@shared_task(name="periodic_task_cleanup")
def periodic_task_cleanup(max_age_days: int = 30) -> None:
    """Called by redbeat. Creates a Task DB row and dispatches delete_tasks."""
    from adapters.database import SessionLocal
    from entities.task import Task, TaskType

    db = SessionLocal()
    try:
        task = Task(
            name=f"Periodic task cleanup (>{max_age_days} days)",
            type=TaskType.DeleteTasks,
            data={"max_age_days": max_age_days},
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

    db = SessionLocal()
    try:
        task = Task(
            name="Periodic sector compaction",
            type=TaskType.CompactSectors,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        dispatch_task(task)
    finally:
        db.close()


TASK_DISPATCH = {
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
}


def dispatch_task(task: Task) -> None:
    """Dispatch a task to Celery based on its type."""
    celery_task = TASK_DISPATCH.get(task.type)
    if celery_task is None:
        raise ValueError(f"Unknown task type: {task.type}")

    kwargs: dict = {"task_id": str(task.task_id)}
    if task.type == TaskType.SyncRecords:
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

    dispatch_task(task)

    return TaskSchema.model_validate(task, from_attributes=True)


async def revoke_task(task: Task, db_session: DatabaseSession) -> TaskSchema:
    """
    Revokes a task if it is in a revocable state.
    """
    if task.status not in {TaskStatus.Started, TaskStatus.Pending}:
        raise ValueError(
            f"Task with status '{task.status}' cannot be revoked."
        )

    tasks_client.control.revoke(
        str(task.task_id), terminate=True, signal="SIGTERM"
    )

    task.status = TaskStatus.Revoked
    task.finished_at = config.timestamp

    task.save(db_session)

    publish_event(TaskStatusEvent(
        task_id=str(task.task_id),
        task_type=task.type.value,
        name=task.name,
        status=task.status.value,
        severity=task.severity.value,
        created_by=str(task.created_by),
    ))

    return TaskSchema.model_validate(task, from_attributes=True)

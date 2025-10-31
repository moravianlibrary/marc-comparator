import logging
from dataclasses import dataclass
from typing import ContextManager, Optional

from celery import Celery
from celery import Task as CeleryTask
from celery import shared_task
from sqlalchemy.orm import Session

from adapters.database import DatabaseSession, get_db_session
from adapters.indexer import IndexerSession, indexer_session
from adapters.lock_server import one_at_a_time_lock
from config import config

# Importing entities to register with the ORM
from entities.catalog_record import CatalogRecord  # noqa: F401
from entities.role import Role  # noqa: F401
from entities.task import Task, TaskSchema, TaskStatus, TaskType
from entities.user import User  # noqa: F401

tasks_client = Celery(
    "tasks",
    broker=config.broker.url,
    broker_connection_retry_on_startup=True,
    result_backend=f"db+{config.postgres.url}",
    timezone=config.timezone,
)

type TasksClient = Celery


class TaskHandler(logging.Handler):
    """
    Logging handler that writes messages to a Task.traceback field.
    """

    def __init__(self, db: Session, task: Task, level=logging.DEBUG):
        super().__init__(level)
        self.db_session = db
        self.task = task

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        timestamp = config.timestamp
        entry = f"[{timestamp}] {record.levelname}: {msg}\n"

        if self.task.traceback:
            self.task.traceback += entry
        else:
            self.task.traceback = entry

        try:
            self.db_session.commit()
        except Exception:
            self.db_session.rollback()


@dataclass
class TaskContext:
    logger: logging.Logger
    db_session: DatabaseSession
    indexer_session: IndexerSession  # TODO: Remove
    task: Task


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
        self.lock: Optional[ContextManager[bool]] = None

        self.db_session = None
        self.task: Task | None = None
        self.logger = None

    async def save_and_index_task(self):
        self.task.save(self.db_session)
        await TaskSchema.model_validate(self.task, from_attributes=True).save()

    async def __aenter__(self) -> TaskContext:
        # --- DB session ---
        self.db_session = get_db_session()

        # --- Load task ---
        self.task = Task.get(self.db_session, self.task_id)

        # --- Logger ---
        self.logger = logging.getLogger(f"task-{self.task_id}")
        handler = TaskHandler(self.db_session, self.task)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # --- Indexer session ---
        self.indexer = await indexer_session().__aenter__()

        # Mark task as started
        self.logger.info("Task started")
        self.task.status = TaskStatus.Started
        self.task.started_at = config.timestamp
        await self.save_and_index_task()

        # --- Acquire lock if needed ---
        if self.lock_key:
            self.lock = one_at_a_time_lock(
                self.lock_key, self.lock_blocking_timeout
            )
            lock_acquired = self.lock.__enter__()
            if not lock_acquired:
                raise ValueError(
                    f"Task lock '{self.lock_key}' is already acquired"
                )

        return TaskContext(
            logger=self.logger,
            db_session=self.db_session,
            indexer_session=self.indexer,
            task=self.task,
        )

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
            await self.save_and_index_task()
        finally:
            # --- Release resources ---
            if self.lock:
                self.lock.__exit__(None, None, None)

            if self.db_session:
                self.db_session.close()


def init_tasks_context() -> None:
    """
    Initializes any global context needed for tasks.
    """
    from adapters.aleph_client_registry import AlephClientRegistry

    if config.aleph_config_path:
        AlephClientRegistry.load_from_config(config.aleph_config_path)


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

    init_tasks_context()
    return async_to_sync(fetch_record_task)(str(self.request.id))


@shared_task(bind=True, name="catalog_sync_task")
def records_sync_task(
    self: CeleryTask, lock_key: str, lock_blocking_timeout: int
):
    from asgiref.sync import async_to_sync

    from catalog_records.tasks import records_sync_task

    init_tasks_context()
    return async_to_sync(records_sync_task)(
        str(self.request.id), lock_key, lock_blocking_timeout
    )


@shared_task(name="validate_records", bind=True)
def validate_records_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from validation.tasks import validate_records

    init_tasks_context()
    return async_to_sync(validate_records)(str(self.request.id))


@shared_task(name="link_records_to_authorities", bind=True)
def link_records_to_authorities(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from authority_linking.tasks import authority_linking

    init_tasks_context()
    return async_to_sync(authority_linking)(str(self.request.id))


@shared_task(name="compare_records", bind=True)
def compare_records_task(self: CeleryTask) -> None:
    from asgiref.sync import async_to_sync

    from comparison.tasks import compare_records

    init_tasks_context()
    return async_to_sync(compare_records)(str(self.request.id))


def dispatch_task(task: Task) -> None:
    """
    Dispatches a task to the Celery based on its type.

    Parameters
    ----------
    task : Task
        The task to be dispatched.
    """
    task_id = str(task.task_id)

    if task.type == TaskType.FetchRecord:
        fetch_record_task.apply_async(task_id=task_id)

    elif task.type == TaskType.SyncRecords:
        lock_key = f"catalog_sync_{task.data['base']}"
        records_sync_task.apply_async(args=[lock_key, 1], task_id=task_id)

    elif task.type == TaskType.ValidateRecords:
        validate_records_task.apply_async(task_id=task_id)

    elif task.type == TaskType.LinkRecordsToAuthorities:
        link_records_to_authorities.apply_async(task_id=task_id)

    elif task.type == TaskType.CompareRecords:
        compare_records_task.apply_async(task_id=task_id)

    else:
        raise ValueError(f"Unknown task type: {task.type}")


async def enqueue_task(task: Task, db_session: DatabaseSession) -> TaskSchema:
    """
    Enqueues a task for processing. Saves the task to the database
    and dispatches it to the Celery worker.

    Parameters
    ----------
    task : Task
        The task to be enqueued.
    db_session : DatabaseSession
        The database session used for saving the task.
    Returns
    -------
    TaskSchema
        The enqueued task as a TaskSchema instance.
    """
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    task_schema = TaskSchema.model_validate(task, from_attributes=True)
    await task_schema.save()

    dispatch_task(task)

    return task_schema


async def revoke_task(task: Task, db_session: DatabaseSession) -> TaskSchema:
    """
    Revokes a task if it is in a revocable state.

    Parameters
    ----------
    task : Task
        The task to be revoked.
    db_session : DatabaseSession
        The database session used for updating the task.
    Returns
    -------
    TaskSchema
        The revoked task as a TaskSchema instance.
    """
    if task.status in {TaskStatus.Started, TaskStatus.Pending}:
        raise ValueError(
            f"Task with status '{task.status}' cannot be revoked."
        )

    tasks_client.control.revoke(
        str(task.task_id), terminate=True, signal="SIGTERM"
    )

    task.status = TaskStatus.Revoked
    task.finished_at = config.timestamp

    task.save(db_session)
    await task.index(db_session)

    return TaskSchema.model_validate(task, from_attributes=True)

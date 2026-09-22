import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import UUID4, BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    UUID,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adapters.database import Base

from ._operations import (
    BaseOperationsMixin,
    RetrievalOperationsMixin,
)


class TaskType(StrEnum):
    FetchRecord = "FetchRecord"
    FetchBatchOfRecords = "FetchBatchOfRecords"
    SyncRecords = "SyncRecords"
    ValidateRecords = "ValidateRecords"
    LinkRecordsToAuthorities = "LinkRecordsToAuthorities"
    CompareRecords = "CompareRecords"
    ProcessRecords = "ProcessRecords"
    DeleteTasks = "DeleteTasks"
    RefreshAnalytics = "RefreshAnalytics"
    CleanupStaleLocks = "CleanupStaleLocks"
    CompactSectors = "CompactSectors"
    RebuildSearchVectors = "RebuildSearchVectors"
    CreateReport = "CreateReport"
    HarvestPlugin = "HarvestPlugin"


class TaskStatus(StrEnum):
    Pending = "Pending"
    Started = "Started"
    Success = "Success"
    # Retry = "Retry"
    Failure = "Failure"
    Revoked = "Revoked"


class TaskSeverity(StrEnum):
    Info = "Info"
    Warning = "Warning"
    Error = "Error"
    Critical = "Critical"


class TaskSchema(BaseModel):
    """Pydantic response model for Task API endpoints (replaces ES IndexerSchema)."""

    task_id: UUID4
    name: str
    type: TaskType
    status: TaskStatus
    severity: TaskSeverity

    created_by: UUID4
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    progress: float | None
    traceback_lines: int

    model_config = ConfigDict(from_attributes=True)


class Task(
    Base,
    BaseOperationsMixin,
    RetrievalOperationsMixin,
):
    __tablename__ = "tasks"

    # Nullability comes from the annotation: Mapped[T] is NOT NULL, Mapped[T | None]
    # is nullable. Explicit SQL types are kept so the DDL matches the migration.
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[TaskType] = mapped_column(Enum(TaskType))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.Pending)
    severity: Mapped[TaskSeverity] = mapped_column(Enum(TaskSeverity), default=TaskSeverity.Info)

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    data: Mapped[dict | None] = mapped_column(JSON)
    # A freshly-created (Pending) task is 0% done, not "unknown"; progress is
    # only set to None mid-run when a task has no countable work-set.
    progress: Mapped[float | None] = mapped_column(Float, default=0.0, server_default="0")
    traceback: Mapped[str | None] = mapped_column(Text)

    # Redelivery attempt counter (poison-message guard under acks_late) and
    # progress heartbeat (orphaned-task reaper). See adapters/tasks.py.
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    heartbeat: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    def __init__(self, **kwargs):
        kwargs.setdefault("task_id", uuid.uuid4())
        kwargs.setdefault("status", TaskStatus.Pending)
        kwargs.setdefault("severity", TaskSeverity.Info)
        kwargs.setdefault("created_at", datetime.now())
        kwargs.setdefault("attempts", 0)
        super().__init__(**kwargs)

    @property
    def traceback_lines(self) -> int:
        return len(self.traceback.splitlines()) if self.traceback else 0

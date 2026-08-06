import uuid
from datetime import datetime

from enum import StrEnum

from pydantic import UUID4, BaseModel
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    UUID,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

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

    class Config:
        from_attributes = True


class Task(
    Base,
    BaseOperationsMixin,
    RetrievalOperationsMixin,
):
    __tablename__ = "tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.Pending)
    severity = Column(Enum(TaskSeverity), nullable=False, default=TaskSeverity.Info)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    started_at = Column(TIMESTAMP, nullable=True)
    finished_at = Column(TIMESTAMP, nullable=True)

    data = Column(JSON, nullable=True)
    # A freshly-created (Pending) task is 0% done, not "unknown"; progress is
    # only set to None mid-run when a task has no countable work-set.
    progress = Column(Float, nullable=True, default=0.0, server_default="0")
    traceback = Column(Text, nullable=True)

    # Redelivery attempt counter (poison-message guard under acks_late) and
    # progress heartbeat (orphaned-task reaper). See adapters/tasks.py.
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    heartbeat = Column(TIMESTAMP, nullable=True)

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

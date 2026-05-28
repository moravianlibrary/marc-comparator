from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, UUID4
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    UUID,
    Column,
    Enum,
    Float,
    ForeignKey,
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
    Base, BaseOperationsMixin, RetrievalOperationsMixin,
):
    __tablename__ = "tasks"

    task_id = Column(
        UUID(as_uuid=True), primary_key=True, default=func.gen_random_uuid()
    )
    name = Column(String(255), nullable=False)
    type = Column(Enum(TaskType), nullable=False)
    status = Column(
        Enum(TaskStatus), nullable=False, default=TaskStatus.Pending
    )
    severity = Column(
        Enum(TaskSeverity), nullable=False, default=TaskSeverity.Info
    )

    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    started_at = Column(TIMESTAMP, nullable=True)
    finished_at = Column(TIMESTAMP, nullable=True)

    data = Column(JSON, nullable=True)
    progress = Column(Float, nullable=True)
    traceback = Column(Text, nullable=True)

    @property
    def traceback_lines(self) -> int:
        return len(self.traceback.splitlines()) if self.traceback else 0

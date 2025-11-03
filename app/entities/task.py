from datetime import datetime
from enum import StrEnum

from esorm.fields import Text as IndexerText
from pydantic import UUID4
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    UUID,
    Column,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)

from adapters.database import Base
from adapters.indexer import IndexerSchema

from ._operations import (
    BaseOperationsMixin,
    IndexerOperationsMixin,
    RetrievalOperationsMixin,
)


class TaskType(StrEnum):
    FetchRecord = "FetchRecord"
    FetchBatchOfRecords = "FetchBatchOfRecords"
    SyncRecords = "SyncRecords"
    ValidateRecords = "ValidateRecords"
    LinkRecordsToAuthorities = "LinkRecordsToAuthorities"
    CompareRecords = "CompareRecords"
    ReindexRecords = "ReindexRecords"
    DeleteTasks = "DeleteTasks"
    RecreateIndexes = "RecreateIndexes"


class TaskStatus(StrEnum):
    Pending = "Pending"
    Started = "Started"
    Success = "Success"
    # Retry = "Retry"
    Failure = "Failure"
    Revoked = "Revoked"


class TaskSchema(IndexerSchema):
    class ESConfig:
        index = "tasks"
        id_field = "task_id"

    task_id: UUID4
    name: IndexerText
    type: TaskType
    status: TaskStatus

    created_by: UUID4
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class Task(
    Base, BaseOperationsMixin, RetrievalOperationsMixin, IndexerOperationsMixin
):
    __indexer_schema__ = TaskSchema
    __tablename__ = "tasks"

    task_id = Column(
        UUID(as_uuid=True), primary_key=True, default=func.gen_random_uuid()
    )
    name = Column(String(255), nullable=False)
    type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.Pending)

    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    started_at = Column(TIMESTAMP, nullable=True)
    finished_at = Column(TIMESTAMP, nullable=True)

    data = Column(JSON, nullable=True)
    traceback = Column(Text, nullable=True)

    @property
    def traceback_lines(self) -> int:
        return len(self.traceback.splitlines()) if self.traceback else 0

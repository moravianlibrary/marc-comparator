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
    PickleType,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from adapters.database import Base
from adapters.indexer import IndexerSchema
from entities._operations import BaseOperationsMixin


class TaskType(StrEnum):
    FetchRecord = "FetchRecord"
    FetchBatchOfRecords = "FetchBatchOfRecords"
    SyncRecords = "SyncRecords"
    ValidateRecords = "ValidateRecords"
    LinkRecordsToAuthorities = "LinkRecordsToAuthorities"
    CompareRecords = "CompareRecords"
    ReindexRecords = "ReindexRecords"


class TaskStatus(StrEnum):
    Pending = "Pending"
    Started = "Started"
    Success = "Success"
    # Retry = "Retry"
    Failure = "Failure"
    Revoked = "Revoked"


class TaskSchema(IndexerSchema):
    class ESConfig:
        index = "categories"
        id_field = "task_id"

    task_id: UUID4
    name: IndexerText
    type: TaskType
    status: TaskStatus

    has_data: bool
    # result: IndexerText | None

    created_by: UUID4
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class Task(Base, BaseOperationsMixin):
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

    traceback = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)
    result = Column(PickleType, nullable=True)

    predecessor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.task_id"),
        nullable=True,
        default=None,
    )
    predecessor = relationship(
        "Task", remote_side=[task_id], backref="successors"
    )

    @property
    def has_data(self) -> bool:
        return self.data is not None

    def get_task(self, db_session) -> "Task":
        task = (
            db_session.query(Task)
            .filter(Task.task_id == str(self.task_id))
            .one_or_none()
        )
        if task is None:
            raise ValueError(f"Task with ID {self.task_id} not found")
        return task

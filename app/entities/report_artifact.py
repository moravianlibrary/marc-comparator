import uuid
from datetime import datetime

from pydantic import UUID4, BaseModel
from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Column,
    ForeignKey,
    LargeBinary,
    String,
    func,
)

from adapters.database import Base

from ._operations import BaseOperationsMixin, RetrievalOperationsMixin


class ReportArtifactSchema(BaseModel):
    """Metadata-only response model (never serialises the blob)."""

    id: UUID4
    task_id: UUID4
    tool: str
    filename: str
    content_type: str
    size: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReportArtifact(Base, BaseOperationsMixin, RetrievalOperationsMixin):
    __tablename__ = "report_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The validator/comparator that produced the artifact (enum value string).
    tool = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False, default="application/zip")
    blob = Column(LargeBinary, nullable=False)
    size = Column(BigInteger, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("created_at", datetime.now())
        super().__init__(**kwargs)

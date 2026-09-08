import uuid
from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict
from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    ForeignKey,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

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

    model_config = ConfigDict(from_attributes=True)


class ReportArtifact(Base, BaseOperationsMixin, RetrievalOperationsMixin):
    __tablename__ = "report_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        index=True,
    )
    # The validator/comparator that produced the artifact (enum value string).
    tool: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String, default="application/zip")
    blob: Mapped[bytes] = mapped_column(LargeBinary)
    size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("created_at", datetime.now())
        super().__init__(**kwargs)

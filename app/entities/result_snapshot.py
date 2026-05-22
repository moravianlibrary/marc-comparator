from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, Integer, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from adapters.database import Base, DatabaseSession


class ResultSnapshot(Base):
    __tablename__ = "result_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    record_id = Column(
        String, ForeignKey("catalog_records.id"), nullable=False
    )
    aspect_name = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())

    __table_args__ = (
        Index("ix_result_snapshots_lookup", "record_id", "aspect_name"),
    )

    @classmethod
    def next_version(
        cls,
        db_session: DatabaseSession,
        record_id: str,
        aspect_name: str,
    ) -> int:
        from sqlalchemy import func as sqlfunc
        result = (
            db_session.query(sqlfunc.max(cls.version))
            .filter_by(record_id=record_id, aspect_name=aspect_name)
            .scalar()
        )
        return (result or 0) + 1

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession

from ._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord
    from .user import User


class RecordReview(Base, BaseOperationsMixin):
    __tablename__ = "record_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    record_id = Column(
        String, ForeignKey("catalog_records.id"), nullable=False
    )
    aspect_name = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reviewed_at = Column(TIMESTAMP, nullable=False, default=func.now())
    status = Column(String, nullable=False, default="current")

    __table_args__ = (
        Index(
            "ix_record_reviews_lookup",
            "record_id", "aspect_name", "status",
        ),
    )

    catalog_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[record_id],
        back_populates="reviews",
        lazy="select",
    )

    reviewer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reviewed_by],
        lazy="select",
    )

    @classmethod
    def find_current(
        cls,
        db_session: DatabaseSession,
        record_id: str,
        aspect_name: str,
    ) -> "RecordReview | None":
        return (
            db_session.query(cls)
            .filter_by(
                record_id=record_id,
                aspect_name=aspect_name,
                status="current",
            )
            .one_or_none()
        )

    @classmethod
    def find_all_current(
        cls,
        db_session: DatabaseSession,
        record_id: str,
    ) -> list["RecordReview"]:
        return (
            db_session.query(cls)
            .filter_by(record_id=record_id, status="current")
            .all()
        )

    @classmethod
    def supersede_current(
        cls,
        db_session: DatabaseSession,
        record_id: str,
        aspect_name: str,
    ) -> None:
        """Set any current review for this aspect to 'superseded'."""
        (
            db_session.query(cls)
            .filter_by(
                record_id=record_id,
                aspect_name=aspect_name,
                status="current",
            )
            .update({"status": "superseded"})
        )

    @classmethod
    def outdate_current(
        cls,
        db_session: DatabaseSession,
        record_id: str,
        aspect_name: str | None = None,
    ) -> None:
        """Mark current review(s) as 'outdated'. If aspect_name is None, outdate all."""
        query = db_session.query(cls).filter_by(
            record_id=record_id, status="current"
        )
        if aspect_name is not None:
            query = query.filter_by(aspect_name=aspect_name)
        query.update({"status": "outdated"})

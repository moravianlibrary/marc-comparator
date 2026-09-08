from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Self
from uuid import UUID as StdUUID
from uuid import uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.database import Base, DatabaseSession

from ._operations import BaseOperationsMixin


class ReviewStatus(StrEnum):
    Current = "current"
    Superseded = "superseded"
    Outdated = "outdated"


if TYPE_CHECKING:
    from .catalog_record import CatalogRecord
    from .user import User


class RecordReview(Base, BaseOperationsMixin):
    __tablename__ = "record_reviews"

    id: Mapped[StdUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    record_id: Mapped[str] = mapped_column(String, ForeignKey("catalog_records.id"))
    aspect_name: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[StdUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())

    # Plain String column — ReviewStatus is only its default, so reads come back as str.
    status: Mapped[str] = mapped_column(String, default=ReviewStatus.Current)

    __table_args__ = (
        Index(
            "ix_record_reviews_lookup",
            "record_id",
            "aspect_name",
            "status",
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
    ) -> Self | None:
        return (
            db_session.query(cls)
            .filter_by(
                record_id=record_id,
                aspect_name=aspect_name,
                status=ReviewStatus.Current,
            )
            .one_or_none()
        )

    @classmethod
    def find_all_current(
        cls,
        db_session: DatabaseSession,
        record_id: str,
    ) -> list[Self]:
        return (
            db_session.query(cls).filter_by(record_id=record_id, status=ReviewStatus.Current).all()
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
                status=ReviewStatus.Current,
            )
            .update({"status": ReviewStatus.Superseded})
        )

    @classmethod
    def outdate_current(
        cls,
        db_session: DatabaseSession,
        record_id: str,
        aspect_name: str | None = None,
    ) -> None:
        """Mark current review(s) as 'outdated'. If aspect_name is None, outdate all."""
        query = db_session.query(cls).filter_by(record_id=record_id, status=ReviewStatus.Current)
        if aspect_name is not None:
            query = query.filter_by(aspect_name=aspect_name)
        query.update({"status": ReviewStatus.Outdated})

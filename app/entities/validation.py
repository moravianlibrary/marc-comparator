from typing import TYPE_CHECKING, Optional

from esorm.fields import Keyword
from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession
from adapters.indexer import IndexerNestedModel

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class AuthorityLinkSchema(IndexerNestedModel):
    base: Keyword
    system_number: Keyword
    confidence: float | None


class Validation(Base):
    __tablename__ = "validations"

    catalog_record_id = Column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    validator = Column(String, primary_key=True)

    result = Column(JSONB, nullable=False)
    updated_at = Column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )

    catalog_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[catalog_record_id],
        back_populates="validations",
        lazy="select",
    )

    @classmethod
    def find(
        cls,
        db_session: "DatabaseSession",
        catalog_record_id: str,
        validator: str,
    ) -> Optional["Validation"]:
        return (
            db_session.query(cls)
            .filter_by(
                catalog_record_id=catalog_record_id,
                validator=validator,
            )
            .one_or_none()
        )

    def save(self, db_session: DatabaseSession) -> "Validation":
        db_session.add(self)
        db_session.commit()
        db_session.refresh(self)
        return self

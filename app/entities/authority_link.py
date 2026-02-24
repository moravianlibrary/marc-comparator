from datetime import datetime
from typing import TYPE_CHECKING, Optional

from esorm.fields import Keyword
from sqlalchemy import TIMESTAMP, Column, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession
from adapters.indexer import IndexerNestedModel
from entities._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class AuthorityLinkSchema(IndexerNestedModel):
    linker: Keyword
    base: Keyword
    system_number: Keyword | None
    confidence: float | None
    updated_at: datetime


class AuthorityLink(Base, BaseOperationsMixin):
    __tablename__ = "authority_links"

    main_record_id = Column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    linker = Column(String, nullable=False, primary_key=True)
    base = Column(String, nullable=False, primary_key=True)

    authority_record_id = Column(
        String,
        ForeignKey("catalog_records.id"),
        nullable=False,
    )

    confidence = Column(Float, nullable=True)
    updated_at = Column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )

    main_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[main_record_id],
        back_populates="authority_links",
        lazy="select",
    )

    authority_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[authority_record_id],
        lazy="select",
    )

    @property
    def system_number(self) -> str:
        return self.authority_record.system_number

    @classmethod
    def find_by_linker_and_base(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        linker: str,
        base: str,
    ) -> Optional["AuthorityLink"]:
        return (
            db_session.query(cls)
            .filter_by(main_record_id=main_record_id, linker=linker, base=base)
            .one_or_none()
        )

    @classmethod
    def find_by_main_record_and_base(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        base: str,
    ) -> Optional["AuthorityLink"]:
        """Return the single authority link for this record and base, if any."""
        return (
            db_session.query(cls)
            .filter_by(main_record_id=main_record_id, base=base)
            .first()
        )

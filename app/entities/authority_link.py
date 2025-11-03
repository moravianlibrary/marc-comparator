from typing import TYPE_CHECKING, Optional

from esorm.fields import Keyword
from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession
from adapters.indexer import IndexerNestedModel
from entities._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class AuthorityLinkSchema(IndexerNestedModel):
    base: Keyword
    system_number: Keyword
    confidence: float | None


class AuthorityLink(Base, BaseOperationsMixin):
    __tablename__ = "authority_links"

    main_record_id = Column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    authority_record_id = Column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    confidence = Column(Float, nullable=True)

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
    def base(self) -> str:
        return self.authority_record.base

    @property
    def system_number(self) -> str:
        return self.authority_record.system_number

    @classmethod
    def find(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        authority_record_id: str,
    ) -> Optional["AuthorityLink"]:
        return (
            db_session.query(cls)
            .filter_by(
                main_record_id=main_record_id,
                authority_record_id=authority_record_id,
            )
            .one_or_none()
        )

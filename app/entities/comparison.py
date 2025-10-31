from typing import TYPE_CHECKING

from esorm.fields import Keyword
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base
from adapters.indexer import IndexerNestedModel

from ._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class AuthorityLinkSchema(IndexerNestedModel):
    base: Keyword
    system_number: Keyword
    confidence: float | None


class Comparison(Base, BaseOperationsMixin):
    __tablename__ = "comparisons"

    main_record_id = Column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    other_record_id = Column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )

    result = Column(JSONB, nullable=False)

    main_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[main_record_id],
        back_populates="comparisons",
        lazy="select",
    )

    other_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[other_record_id],
        lazy="select",
    )

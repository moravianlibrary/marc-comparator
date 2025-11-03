from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from esorm.fields import Keyword
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    LargeBinary,
    String,
    event,
    func,
)
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession
from adapters.indexer import IndexerSchema
from entities.comparison import Comparison
from entities.validation import Validation

from ._operations import (
    BaseOperationsMixin,
    IndexerOperationsMixin,
    RetrievalOperationsMixin,
)
from .authority_link import AuthorityLink, AuthorityLinkSchema


class CatalogRecordSource(StrEnum):
    Main = "Main"
    AuthorityLinker = "AuthorityLinker"


class CatalogRecordSchema(IndexerSchema):
    class ESConfig:
        index = "catalog_records"
        id_field = "id"

    id: str

    base: Keyword
    system_number: Keyword

    last_sync: datetime
    deleted: bool

    authority_links: List[AuthorityLinkSchema]


class CatalogRecord(
    Base, BaseOperationsMixin, RetrievalOperationsMixin, IndexerOperationsMixin
):
    __indexer_schema__ = CatalogRecordSchema
    __tablename__ = "catalog_records"

    id = Column(String, primary_key=True)
    base = Column(String, nullable=False)
    system_number = Column(String, nullable=False)

    marc = Column(LargeBinary, nullable=False)

    last_sync = Column(TIMESTAMP, nullable=False, default=func.now())
    deleted = Column(Boolean, nullable=False, default=False)

    source_type = Column(
        String, nullable=False, default=CatalogRecordSource.Main
    )
    source_name = Column(String, nullable=True)

    authority_links: Mapped[List["AuthorityLink"]] = relationship(
        "AuthorityLink",
        foreign_keys=[AuthorityLink.main_record_id],
        back_populates="main_record",
        lazy="select",
    )
    comparisons: Mapped[List["Comparison"]] = relationship(
        "Comparison",
        foreign_keys=[Comparison.main_record_id],
        back_populates="main_record",
        lazy="select",
    )
    validations: Mapped[List[Validation]] = relationship(
        "Validation",
        foreign_keys=[Validation.catalog_record_id],
        back_populates="catalog_record",
        lazy="select",
    )

    @classmethod
    def generate_id(cls, base: str, system_number: str) -> str:
        return f"{base}-{system_number}"

    @classmethod
    def find_by_base_and_system_number(
        cls, db_session: DatabaseSession, base: str, system_number: str
    ) -> Optional["CatalogRecord"]:
        return cls.find(db_session, cls.generate_id(base, system_number))


@event.listens_for(CatalogRecord, "before_insert")
def set_id_before_insert(
    mapper,  # unused # noqa: F841
    connection,  # unused # noqa: F841
    target: CatalogRecord,
):
    if not target.id:
        target.id = CatalogRecord.generate_id(
            target.base, target.system_number
        )

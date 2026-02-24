from datetime import datetime
from enum import StrEnum
from functools import cached_property
from typing import List, Optional

from esorm.fields import Keyword, Text, TextField
from marcdantic import MarcRecord
from marcdantic.selectors import SubtitleJq, TitleJq
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
from adapters.indexer import EnumList, IndexerSchema

from ._operations import (
    BaseOperationsMixin,
    IndexerOperationsMixin,
    RetrievalOperationsMixin,
)
from .authority_link import AuthorityLink, AuthorityLinkSchema
from .comparison import Comparison, ComparisonSchema
from .validation import Validation, ValidationSchema


class CatalogRecordSource(StrEnum):
    Main = "Main"
    AuthorityLinker = "AuthorityLinker"


class CatalogRecordState(StrEnum):
    Active = "Active"
    Deleted = "Deleted"
    Visible = "Visible"
    Hidden = "Hidden"
    Unprocessed = "Unprocessed"
    Processed = "Processed"


class CatalogRecordSchema(IndexerSchema):
    class ESConfig:
        index = "catalog-records"
        id_field = "id"

    id: str

    base: Keyword
    system_number: Keyword

    type_of_record: Keyword
    bibliographic_level: Keyword

    title: Text | None = TextField(None, keyword=True)
    subtitle: Text | None
    authors: List[Text]
    latest_transaction: datetime
    latest_sync: datetime
    processed_at: datetime | None

    state: EnumList[CatalogRecordState]

    authority_links: List[AuthorityLinkSchema]
    comparisons: List[ComparisonSchema]
    validations: List[ValidationSchema]


class CatalogRecord(
    Base, BaseOperationsMixin, RetrievalOperationsMixin, IndexerOperationsMixin
):
    __indexer_schema__ = CatalogRecordSchema
    __tablename__ = "catalog_records"

    id = Column(String, primary_key=True)
    base = Column(String, nullable=False)
    system_number = Column(String, nullable=False)

    _marc = Column(LargeBinary, name="marc", nullable=False)

    latest_sync = Column(TIMESTAMP, nullable=False, default=func.now())
    deleted = Column(Boolean, nullable=False, default=False)
    hidden = Column(Boolean, nullable=False, default=False)
    processed_at = Column(TIMESTAMP, nullable=True)

    source_type = Column(
        String, nullable=False, default=CatalogRecordSource.Main
    )
    source_name = Column(String, nullable=True)

    authority_links: Mapped[List[AuthorityLink]] = relationship(
        "AuthorityLink",
        foreign_keys=[AuthorityLink.main_record_id],
        back_populates="main_record",
        lazy="select",
    )
    comparisons: Mapped[List[Comparison]] = relationship(
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

    @property
    def marc(self) -> bytes:
        return self._marc

    @marc.setter
    def marc(self, value: bytes):
        self._marc = value
        # Invalidate cached property
        if "record" in self.__dict__:
            del self.__dict__["record"]

    @cached_property
    def record(self) -> MarcRecord:
        return MarcRecord.from_mrc(self._marc)

    @property
    def type_of_record(self) -> str:
        return self.record.leader_selector.type_of_record

    @property
    def bibliographic_level(self) -> str:
        return self.record.leader_selector.bibliographic_level

    @property
    def title(self) -> str | None:
        stm = self.record.variable_fields.query_subfield_values(TitleJq)
        return stm[0] if stm else None

    @property
    def subtitle(self) -> str | None:
        stm = self.record.variable_fields.query_subfield_values(SubtitleJq)
        return stm[0] if stm else None

    @property
    def authors(self) -> List[str]:
        return self.record.variable_fields.query_subfield_values(
            '.["100"]?[]?.subfields.a[]?'
        )

    @property
    def latest_transaction(self) -> datetime | None:
        return self.record.control_fields_selector.latest_transaction

    @property
    def state(self) -> List[CatalogRecordState]:
        states = []

        if not self.deleted:
            states.append(CatalogRecordState.Active)
        else:
            states.append(CatalogRecordState.Deleted)

        if self.hidden:
            states.append(CatalogRecordState.Hidden)
        else:
            states.append(CatalogRecordState.Visible)

        if self.processed_at is not None:
            states.append(CatalogRecordState.Processed)
        else:
            states.append(CatalogRecordState.Unprocessed)

        return states


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

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from marc_comparator.comparators import MatchQuality
from marc_comparator.validators import ValidityStatus
from marcdantic import MarcRecord
from marcdantic.selectors import SubtitleJq, TitleJq
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Index,
    String,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, Session, relationship

from adapters.database import Base, DatabaseSession

from ._operations import (
    BaseOperationsMixin,
    RetrievalOperationsMixin,
)
from .authority_link import AuthorityLink
from .comparison import Comparison
from .record_review import RecordReview, ReviewStatus
from .validation import Validation


class CatalogRecordSource(StrEnum):
    Main = "Main"
    AuthorityLinker = "AuthorityLinker"


class CatalogRecordState(StrEnum):
    Active = "Active"
    Deleted = "Deleted"
    Unprocessed = "Unprocessed"
    Processed = "Processed"
    Reviewed = "Reviewed"
    PartiallyReviewed = "PartiallyReviewed"
    Unreviewed = "Unreviewed"
    ReviewNotNeeded = "ReviewNotNeeded"


class CatalogRecord(
    Base, BaseOperationsMixin, RetrievalOperationsMixin,
):
    __tablename__ = "catalog_records"

    id = Column(String, primary_key=True)
    base = Column(String, nullable=False)
    system_number = Column(String, nullable=False)
    title = Column(String, nullable=True)
    authors = Column(ARRAY(String), nullable=False, default=[])

    latest_sync = Column(TIMESTAMP, nullable=False, default=func.now())
    deleted = Column(Boolean, nullable=False, default=False)
    processed_at = Column(TIMESTAMP, nullable=True)

    source_type = Column(
        String, nullable=False, default=CatalogRecordSource.Main
    )
    source_name = Column(String, nullable=True)

    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    _type_of_record = Column("type_of_record", String, nullable=True)
    _bibliographic_level = Column("bibliographic_level", String, nullable=True)
    latest_transaction = Column(TIMESTAMP, nullable=True)

    search_text = Column(String, nullable=True)
    search_vector = Column(TSVECTOR)

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
    reviews: Mapped[List[RecordReview]] = relationship(
        "RecordReview",
        foreign_keys=[RecordReview.record_id],
        back_populates="catalog_record",
        lazy="select",
    )

    __table_args__ = (
        Index("idx_catalog_records_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_catalog_records_updated_at", "updated_at"),
    )

    @classmethod
    def generate_id(cls, base: str, system_number: str) -> str:
        return f"{base}-{system_number}"

    @classmethod
    def find_by_base_and_system_number(
        cls, db_session: DatabaseSession, base: str, system_number: str
    ) -> Optional["CatalogRecord"]:
        return cls.find(db_session, cls.generate_id(base, system_number))

    def get_marc(self, db_session: Session) -> bytes:
        """Read MARC bytes from sector storage."""
        from adapters.marc_sectors import read_marc

        data = read_marc(db_session, self.base, self.system_number)
        if data is None:
            raise ValueError(f"MARC data not found for {self.id}")
        return data

    def get_record(self, db_session: Session) -> MarcRecord:
        """Parse MARC record from sector storage."""
        return MarcRecord.from_mrc(self.get_marc(db_session))

    @property
    def type_of_record(self) -> str | None:
        return self._type_of_record

    @type_of_record.setter
    def type_of_record(self, value: str):
        self._type_of_record = value

    @property
    def bibliographic_level(self) -> str | None:
        return self._bibliographic_level

    @bibliographic_level.setter
    def bibliographic_level(self, value: str):
        self._bibliographic_level = value

    @property
    def state(self) -> List[CatalogRecordState]:
        states = []

        if not self.deleted:
            states.append(CatalogRecordState.Active)
        else:
            states.append(CatalogRecordState.Deleted)

        if self.processed_at is not None:
            states.append(CatalogRecordState.Processed)
        else:
            states.append(CatalogRecordState.Unprocessed)

        current_reviews = {r.aspect_name for r in self.reviews if r.status == ReviewStatus.Current}
        # Aspects that need review: non-excellent comparators + validators with issues
        aspects_needing_review = (
            {c.comparator for c in self.comparisons
             if c.match_quality != MatchQuality.Excellent}
            | {v.validator for v in self.validations
               if v.status not in (ValidityStatus.Valid, ValidityStatus.AdditionalInfo)}
        )
        if not aspects_needing_review:
            states.append(CatalogRecordState.ReviewNotNeeded)
        elif current_reviews >= aspects_needing_review:
            states.append(CatalogRecordState.Reviewed)
        elif current_reviews & aspects_needing_review:
            states.append(CatalogRecordState.PartiallyReviewed)
        else:
            states.append(CatalogRecordState.Unreviewed)

        return states

    def update_search_text_from(self, record: MarcRecord):
        """Update title, authors, and search_text from a parsed MARC record."""
        title_vals = record.variable_fields.query_subfield_values(TitleJq)
        subtitle_vals = record.variable_fields.query_subfield_values(SubtitleJq)
        author_vals = record.variable_fields.query_subfield_values(
            '.["100"]?[]?.subfields.a[]?'
        )

        self.title = title_vals[0] if title_vals else None
        self.authors = author_vals or []

        parts = [self.system_number]
        if title_vals:
            parts.append(title_vals[0])
        if subtitle_vals:
            parts.append(subtitle_vals[0])
        parts.extend(author_vals)
        self.search_text = " ".join(filter(None, parts))


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

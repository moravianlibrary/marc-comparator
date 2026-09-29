from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Optional

from marc_comparator.comparators import MatchQuality
from marc_comparator.validators import ValidityStatus
from marcdantic import MarcRecord
from marcdantic.selectors import SubtitleJq, TitleJq
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Index,
    String,
    and_,
    event,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from adapters.database import Base, DatabaseSession

from ._operations import (
    BaseOperationsMixin,
    RetrievalOperationsMixin,
)
from .authority_link import ANSWER_RANK, AuthorityLink, LinkOutcome
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
    #: The last pass could not read this record. Distinct from Unprocessed,
    #: which says only that no pass has finished with it yet.
    Broken = "Broken"
    Reviewed = "Reviewed"
    PartiallyReviewed = "PartiallyReviewed"
    Unreviewed = "Unreviewed"
    ReviewNotNeeded = "ReviewNotNeeded"


class CatalogRecord(
    Base,
    BaseOperationsMixin,
    RetrievalOperationsMixin,
):
    __tablename__ = "catalog_records"

    # Nullability comes from the annotation: Mapped[T] is NOT NULL, Mapped[T | None]
    # is nullable. Explicit SQL types are kept so the DDL matches the migration.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    base: Mapped[str] = mapped_column(String)
    system_number: Mapped[str] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    # default=list, not default=[] — a literal would be shared by every instance.
    authors: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    latest_sync: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    #: Why the last processing attempt could not read this record, or null.
    #:
    #: A record whose MARC will not parse produces nothing — no comparisons, no
    #: validations — and never gets stamped, so without this it reads as merely
    #: not reached yet and, having no results to review, as needing no review.
    #: Two readings that are both wrong and neither of which anybody can act on.
    #: Cleared the moment a pass gets through the record.
    processing_error: Mapped[str | None] = mapped_column(String)

    # source_type is a plain String column, not a DB enum — CatalogRecordSource is only
    # its default, so reads come back as str. Annotating the enum here would be a lie.
    source_type: Mapped[str] = mapped_column(String, default=CatalogRecordSource.Main)
    source_name: Mapped[str | None] = mapped_column(String)

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    _type_of_record: Mapped[str | None] = mapped_column("type_of_record", String)
    _bibliographic_level: Mapped[str | None] = mapped_column("bibliographic_level", String)
    latest_transaction: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    search_text: Mapped[str | None] = mapped_column(String)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    #: What this record was found to be the same work as.
    #:
    #: Scoped to the answer rows that are links. The table also holds rows
    #: saying why a record has no link, and every reader of this relationship
    #: means "the same work" — listing them, filtering on them, comparing
    #: against them. Putting the guard here puts it in one place; leaving it to
    #: the call sites means each of them can forget it, and the one that does
    #: reports a link to nothing.
    authority_links: Mapped[list[AuthorityLink]] = relationship(
        "AuthorityLink",
        primaryjoin=lambda: and_(
            CatalogRecord.id == AuthorityLink.main_record_id,
            AuthorityLink.rank == ANSWER_RANK,
            AuthorityLink.outcome == LinkOutcome.Linked,
        ),
        viewonly=True,
        lazy="select",
    )
    #: Everything the linkers had to say about this record, links and gaps
    #: alike, in the order they would be shown.
    link_attempts: Mapped[list[AuthorityLink]] = relationship(
        "AuthorityLink",
        foreign_keys=[AuthorityLink.main_record_id],
        back_populates="main_record",
        order_by=lambda: (AuthorityLink.base, AuthorityLink.rank),
        lazy="select",
    )
    comparisons: Mapped[list[Comparison]] = relationship(
        "Comparison",
        foreign_keys=[Comparison.main_record_id],
        back_populates="main_record",
        lazy="select",
    )
    validations: Mapped[list[Validation]] = relationship(
        "Validation",
        foreign_keys=[Validation.catalog_record_id],
        back_populates="catalog_record",
        lazy="select",
    )
    reviews: Mapped[list[RecordReview]] = relationship(
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
    def warm(cls, db_session: Session, record_ids: Sequence[str]) -> None:
        """Load a window of records into the session in one query.

        The loops that walk a window ask for each record with ``Session.get``,
        which answers from the identity map when the row is already loaded and
        goes to the database when it is not. Filling the map up front therefore
        turns a query per record into one per window, without any caller having
        to hold the instances — which it must not do anyway, since ManagedTask
        cycles the session every ``commit_interval`` records and detaches them.

        Safe precisely because it is only a warm-up: after a cycle the map is
        empty again and the next ``get`` queries exactly as it did before.
        """

        if not record_ids:
            return

        rows = db_session.execute(select(cls).where(cls.id.in_(record_ids))).scalars().all()

        # The identity map holds *weak* references. Letting these fall out of
        # scope here collects them straight back out of it, and every get()
        # afterwards queries again — which is what the first version of this
        # did, silently and with no way to tell from the outside. Session.info
        # lives exactly as long as the session, so a cycled session drops them
        # of its own accord.
        db_session.info["warmed_window"] = rows

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
        from adapters.marc_sectors import read_stored_marc

        return read_stored_marc(self.get_marc(db_session))

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
    def state(self) -> list[CatalogRecordState]:
        states = []

        if not self.deleted:
            states.append(CatalogRecordState.Active)
        else:
            states.append(CatalogRecordState.Deleted)

        if self.processed_at is not None:
            states.append(CatalogRecordState.Processed)
        else:
            states.append(CatalogRecordState.Unprocessed)

        if self.processing_error is not None:
            # No review status at all for a record nobody could read. Every one
            # of the four below is derived from comparisons and validations, and
            # a broken record has none — which is how it used to come out as
            # ReviewNotNeeded and sit in the interface looking clean.
            states.append(CatalogRecordState.Broken)
            return states

        current_reviews = {r.aspect_name for r in self.reviews if r.status == ReviewStatus.Current}
        # Aspects that need review: non-excellent comparators + validators with issues
        aspects_needing_review = {
            c.comparator for c in self.comparisons if c.match_quality != MatchQuality.Excellent
        } | {
            v.validator
            for v in self.validations
            if v.status not in (ValidityStatus.Valid, ValidityStatus.AdditionalInfo)
        }
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
        author_vals = record.variable_fields.query_subfield_values('.["100"]?[]?.subfields.a[]?')

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
        target.id = CatalogRecord.generate_id(target.base, target.system_number)

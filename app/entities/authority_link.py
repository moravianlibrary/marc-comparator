from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TIMESTAMP, Float, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship

from adapters.database import Base, DatabaseSession
from entities._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class LinkOutcome(StrEnum):
    """What came of trying to link one record to one target base.

    The table used to hold only the first of these, so every other way of
    ending up without a link — the lookup found nothing, the lookup never
    completed, the best candidate was not good enough — was stored as the
    absence of a row, and read back as the same thing.
    """

    #: This is the match. Carries an authority record.
    Linked = "Linked"
    #: Considered and scored, but another candidate was chosen.
    Rejected = "Rejected"
    #: The best candidate did not clear its route's minimum confidence.
    BelowFloor = "BelowFloor"
    #: Something disqualified every candidate — a conflicting national
    #: bibliography number, publication years too far apart, a different kind
    #: of record. Kept apart from ``BelowFloor`` because the two call for
    #: opposite responses: a low score invites a look, a contradiction says
    #: the catalogue holds no counterpart and the search was pointed wrong.
    Conflicting = "Conflicting"
    #: A cataloguer looked at the candidates and ruled them out. A reason
    #: there is no link, like the three above it, and kept apart from them for
    #: the same reason: a low score invites a look and a contradiction says
    #: the search was pointed wrong, while this says the question is settled
    #: and no linker should be re-run hoping for a different answer.
    #:
    #: Who decided is not recorded here — that is what ``link_claims`` is for,
    #: and an accepted claim still reads as ``Linked``. What this records is
    #: the outcome, not its provenance.
    Refused = "Refused"
    #: The lookup completed and found nothing to consider.
    NoCandidate = "NoCandidate"
    #: The lookup did not complete, which is not an answer about the record.
    LookupFailed = "LookupFailed"


#: The rank of the row that answers "what is this record linked to".
#:
#: Named because it is a claim, not an index: exactly one row per record and
#: base sits here, and the primary key is what enforces that. Everything below
#: it is a runner-up.
ANSWER_RANK = 0


class AuthorityLink(Base, BaseOperationsMixin):
    __tablename__ = "authority_links"

    __table_args__ = (
        # One row per candidate per record and base, however many linkers
        # propose it. Partial, because the rows this must not constrain are
        # exactly the ones naming no candidate — and the primary key already
        # allows a record only one of those.
        Index(
            "uq_authority_links_candidate",
            "main_record_id",
            "base",
            "authority_base",
            "authority_sysno",
            unique=True,
            postgresql_where=text("authority_sysno IS NOT NULL"),
        ),
        Index("ix_authority_links_outcome", "outcome"),
    )

    main_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    base: Mapped[str] = mapped_column(String, primary_key=True)
    #: Position in this record's list for this base, ``ANSWER_RANK`` first.
    #:
    #: In the key rather than alongside it so that "there is one answer" is a
    #: property of the schema. A flag saying the same thing can disagree with
    #: the ordering; a key cannot.
    rank: Mapped[int] = mapped_column(Integer, primary_key=True, default=ANSWER_RANK)

    #: Who proposed this row, or nothing where no one did.
    #:
    #: Deliberately not part of the key: both linkers run for every record and
    #: may propose the same authority record, and the interface has to show a
    #: cataloguer one ordered list either way. Null on a row that records the
    #: absence of a link, because every linker was asked and none of them
    #: answered — naming one of them would blame it for a unanimous silence.
    linker: Mapped[str | None] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String, default=LinkOutcome.Linked)

    #: The candidate's natural key, which is what identifies it.
    #:
    #: ``CatalogRecord.generate_id`` is ``f"{base}-{system_number}"``, so the
    #: foreign key below carries no information these two do not — it only
    #: forces a row to exist. A row that never became the answer therefore
    #: needs no persisted copy of the record, and a row that says why there is
    #: no answer names no record at all.
    authority_base: Mapped[str | None] = mapped_column(String)
    authority_sysno: Mapped[str | None] = mapped_column(String)
    authority_record_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("catalog_records.id"),
    )

    confidence: Mapped[float | None] = mapped_column(Float)
    #: How the linker found this candidate — see the SDK's ``MatchRoute``.
    #: Without it a low confidence is unreadable: it could mean two records
    #: that share an ISBN and describe it differently, or a candidate that only
    #: ever shared a title. Null on links written before the linkers reported
    #: it, and by linkers that do not.
    matched_by: Mapped[str | None] = mapped_column(String)
    #: Which identifier found it, where `matched_by` says an identifier did.
    #:
    #: The route alone cannot be read: a pair sharing a national bibliography
    #: number and a pair sharing an ISSN are both "found by identifier", and a
    #: low score means opposite things for the two. Null where the candidate
    #: was found by title, and on links written before the column existed —
    #: the update guard refills those.
    matched_identifier: Mapped[str | None] = mapped_column(String)
    #: How many candidates were weighed in total, which the stored rows do not
    #: say: an unambiguous winner is stored without its runner-ups, so without
    #: this "there were four and three were not worth keeping" is
    #: indistinguishable from "there was only one".
    candidate_count: Mapped[int | None] = mapped_column(Integer)
    #: Free text for an outcome that has something to explain — the error a
    #: failed lookup raised, and nothing at all for the rest.
    detail: Mapped[str | None] = mapped_column(String)

    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    main_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[main_record_id],
        back_populates="link_attempts",
        lazy="select",
    )

    authority_record: Mapped[Optional["CatalogRecord"]] = relationship(
        "CatalogRecord",
        foreign_keys=[authority_record_id],
        lazy="select",
    )

    def _as_link(self) -> None:
        """Raise unless this row is an accepted link.

        Every row now has an outcome, and only one of them means "these two
        records are the same work". The accessors below are how a caller that
        means that says so: they are reached through the scoped relationship
        and the scoped finders, so a row without a record here is a reader that
        escaped the scoping, not data anyone can fix.
        """

        if self.outcome != LinkOutcome.Linked:
            raise ValueError(
                f"{self.main_record_id} -> {self.base} is a {self.outcome} row, not a link"
            )

    @property
    def linked_record(self) -> "CatalogRecord":
        """The authority record this link points at."""

        self._as_link()
        if self.authority_record is None:
            raise ValueError(f"{self.main_record_id} -> {self.base} has no authority record")
        return self.authority_record

    @property
    def linked_record_id(self) -> str:
        """The id of the record this link points at, without loading it.

        Separate from ``linked_record`` because the search listing reads only
        the id, and reaching it through the relationship would be one query per
        link on the busiest read in the system.
        """

        self._as_link()
        if self.authority_record_id is None:
            raise ValueError(f"{self.main_record_id} -> {self.base} has no authority record")
        return self.authority_record_id

    @property
    def linked_by(self) -> str:
        """The linker that proposed this link."""

        self._as_link()
        if self.linker is None:
            raise ValueError(f"{self.main_record_id} -> {self.base} names no linker")
        return self.linker

    @property
    def system_number(self) -> str | None:
        """The candidate's system number, without loading the record for it.

        Rows written before ``authority_sysno`` existed fall back to the record
        they point at; rows that point at nothing have neither and say so.
        """

        if self.authority_sysno is not None:
            return self.authority_sysno
        return self.authority_record.system_number if self.authority_record else None

    @classmethod
    def find_by_main_record_and_base(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        base: str,
    ) -> Optional["AuthorityLink"]:
        """Return the accepted link for this record and base, if there is one.

        A record with no link still has a row at ``ANSWER_RANK`` saying why,
        and that row is not a link: callers here mean "what is this record
        linked to", and answering with a ``NoCandidate`` row would report a
        link to nothing.

        The authority record comes with it: callers reach straight through to
        it, and the relationship is lazy, so leaving it out costs a second
        query per link to read one column.
        """
        return (
            db_session.query(cls)
            .options(joinedload(cls.authority_record))
            .filter_by(
                main_record_id=main_record_id,
                base=base,
                rank=ANSWER_RANK,
                outcome=LinkOutcome.Linked,
            )
            .first()
        )

    @classmethod
    def for_record_and_base(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        base: str,
    ) -> Sequence["AuthorityLink"]:
        """Every row for this record and base, answer first.

        Unlike ``find_by_main_record_and_base`` this is the whole list rather
        than the accepted link: what was considered, in the order it was
        ranked, including the row that says why there is no link. What a
        cataloguer is shown, and what a claim is applied over.
        """

        return (
            db_session.query(cls)
            .filter_by(main_record_id=main_record_id, base=base)
            .order_by(cls.rank)
            .all()
        )

    @classmethod
    def find_candidates_for(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        base: str,
    ) -> Sequence["AuthorityLink"]:
        """The runner-ups this record's answer was chosen over, best first.

        The alternatives to show somebody who does not believe the answer.
        Not every candidate that was weighed — an unambiguous winner keeps
        none — which is what ``candidate_count`` on the answer row is for.
        """
        return (
            db_session.query(cls)
            .filter(
                cls.main_record_id == main_record_id,
                cls.base == base,
                cls.rank > ANSWER_RANK,
            )
            .order_by(cls.rank)
            .all()
        )

    @classmethod
    def find_answer(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        base: str,
    ) -> Optional["AuthorityLink"]:
        """The row at ``ANSWER_RANK``, whatever it says.

        Distinct from ``find_by_main_record_and_base``: this is for the writer,
        which has to clear whatever is sitting in that slot before putting its
        own answer there, and for which a gap row is just as much in the way as
        a link.
        """
        return (
            db_session.query(cls)
            .filter_by(main_record_id=main_record_id, base=base, rank=ANSWER_RANK)
            .one_or_none()
        )

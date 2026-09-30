from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional
from uuid import UUID as StdUUID

from sqlalchemy import TIMESTAMP, Boolean, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.database import Base, DatabaseSession

from ._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord
    from .user import User


class ClaimVerdict(StrEnum):
    """What a cataloguer said about one pair of records.

    Not a score and not an outcome: a person looked at both records and said
    whether they describe the same work. The linkers can be re-run, retuned or
    replaced and this still stands — it is the only statement in the system
    that is not a machine's opinion.
    """

    #: This is the match, whatever the linkers think.
    SameWork = "SameWork"
    #: These are different works, whatever the linkers think.
    NotSameWork = "NotSameWork"


class LinkClaim(Base, BaseOperationsMixin):
    """A cataloguer's verdict on one record and one candidate.

    Keyed by the candidate's natural key rather than by a catalogue row,
    for the reason ``AuthorityLink`` gives: a candidate nobody accepted has no
    row in our catalogue, and a claim has to be able to name one — rejecting
    the machine's answer in favour of a runner-up is the whole point.

    Several claims can stand for one record and base. A cataloguer working
    through a shortlist rules out three candidates and accepts a fourth, and
    each of those is a separate statement about a separate pair.
    """

    __tablename__ = "link_claims"

    main_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    #: The target base this claim is about, matching ``AuthorityLink.base``.
    base: Mapped[str] = mapped_column(String, primary_key=True)
    #: The claimed record's natural key.
    authority_base: Mapped[str] = mapped_column(String, primary_key=True)
    authority_sysno: Mapped[str] = mapped_column(String, primary_key=True)

    # Plain String column — ClaimVerdict is only what writes it, so reads come
    # back as str, the same way RecordReview.status does.
    verdict: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)

    claimed_by: Mapped[StdUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    claimed_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())

    #: What the claimed candidate scored when the claim was made, and what the
    #: best rival scored beside it.
    #:
    #: Kept because the question worth asking later is not "has this score
    #: changed" but "has the evidence moved *against* this claim". A claimed
    #: record whose score improves — because somebody fixed one of the two
    #: catalogues, which is what this tool is for — has not become more
    #: doubtful, and re-raising it every time that happens would train
    #: cataloguers to dismiss the flag. What matters is the gap: see
    #: ``margin_moved_against``.
    claimed_confidence: Mapped[float | None] = mapped_column(Float)
    rival_confidence: Mapped[float | None] = mapped_column(Float)

    #: Set when the gap has moved far enough against the claim to be worth a
    #: second look. Advisory only — the claim still decides the answer. A
    #: machine does not overrule a person because its own numbers moved.
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    __table_args__ = (
        Index("ix_link_claims_lookup", "main_record_id", "base"),
        Index("ix_link_claims_needs_review", "needs_review"),
    )

    catalog_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[main_record_id],
        lazy="select",
    )
    claimant: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[claimed_by],
        lazy="select",
    )

    @property
    def authority_key(self) -> tuple[str, str]:
        """The candidate this claim is about, as the linkers name it."""

        return (self.authority_base, self.authority_sysno)

    @property
    def is_same_work(self) -> bool:
        return self.verdict == ClaimVerdict.SameWork

    def margin_moved_against(self, claimed_now: float | None, rival_now: float | None) -> bool:
        """Whether the evidence has shifted against this claim since it was made.

        Compares gaps, not scores. At claim time the claimed record was
        ``claimed_confidence`` and its best rival ``rival_confidence``; the
        cataloguer saw that gap and decided anyway. The claim is worth
        revisiting only when a rival has gained on it *beyond* the gap the
        cataloguer already overruled.

        A claim made without a snapshot — because neither side had a score —
        has nothing to compare, and never asks for review on this ground.
        """

        if self.claimed_confidence is None or self.rival_confidence is None:
            return False
        if claimed_now is None or rival_now is None:
            return False

        return (rival_now - claimed_now) > (self.rival_confidence - self.claimed_confidence)

    @classmethod
    def for_record(
        cls, db_session: DatabaseSession, main_record_id: str, base: str
    ) -> Sequence["LinkClaim"]:
        return (
            db_session.query(cls)
            .filter_by(main_record_id=main_record_id, base=base)
            .order_by(cls.claimed_at)
            .all()
        )

    @classmethod
    def for_records(
        cls, db_session: DatabaseSession, main_record_ids: Sequence[str], base: str
    ) -> dict[str, list["LinkClaim"]]:
        """Every claim for a window of records, in one query.

        Linking walks records in windows and most of them have no claim at
        all; asking per record would be a query each to learn that.
        """

        if not main_record_ids:
            return {}

        claims: dict[str, list[LinkClaim]] = {}
        rows = (
            db_session.query(cls)
            .filter(cls.main_record_id.in_(list(main_record_ids)), cls.base == base)
            .order_by(cls.claimed_at)
            .all()
        )
        for row in rows:
            claims.setdefault(row.main_record_id, []).append(row)
        return claims

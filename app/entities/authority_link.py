from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TIMESTAMP, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship

from adapters.database import Base, DatabaseSession
from entities._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class AuthorityLink(Base, BaseOperationsMixin):
    __tablename__ = "authority_links"

    main_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    linker: Mapped[str] = mapped_column(String, primary_key=True)
    base: Mapped[str] = mapped_column(String, primary_key=True)

    authority_record_id: Mapped[str] = mapped_column(
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
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

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
        """Return the single authority link for this record and base, if any.

        The authority record comes with it: callers reach straight through to
        it — ``system_number`` below is a property that does — and the
        relationship is lazy, so leaving it out costs a second query per link
        to read one column.
        """
        return (
            db_session.query(cls)
            .options(joinedload(cls.authority_record))
            .filter_by(main_record_id=main_record_id, base=base)
            .first()
        )

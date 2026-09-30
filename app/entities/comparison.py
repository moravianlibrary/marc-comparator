from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Optional

from marc_comparator.comparators import (
    FieldComparisonResult,
    MatchQuality,
    RecordComparisonResult,
)
from sqlalchemy import TIMESTAMP, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.database import Base, DatabaseSession

from ._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class Comparison(Base, BaseOperationsMixin):
    __tablename__ = "comparisons"

    main_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    comparator: Mapped[str] = mapped_column(String, primary_key=True)
    base: Mapped[str] = mapped_column(String, primary_key=True)
    other_record_id: Mapped[str] = mapped_column(String, ForeignKey("catalog_records.id"))

    _result: Mapped[dict] = mapped_column("result", JSONB)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

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

    @classmethod
    def find(
        cls,
        db_session: DatabaseSession,
        main_record_id: str,
        comparator: str,
        base: str,
    ) -> Optional["Comparison"]:
        return (
            db_session.query(cls)
            .filter_by(
                main_record_id=main_record_id,
                comparator=comparator,
                base=base,
            )
            .one_or_none()
        )

    @property
    def system_number(self) -> str:
        return self.other_record.system_number

    @property
    def result(self) -> dict:
        return self._result

    @result.setter
    def result(self, value: dict):
        self._result = value
        # Invalidate cached property
        vars(self).pop("record_result", None)

    @cached_property
    def record_result(self) -> RecordComparisonResult:
        return RecordComparisonResult.model_validate(self._result)

    @property
    def match_quality(self) -> MatchQuality:
        """The band the comparator put this comparison in.

        Read back rather than recomputed. The two literals that used to be
        here were one of three copies of the same bands — the analytics SQL
        held the other two — and a comparison's band is now decided once, by
        the comparator that produced the score, and stored beside it.
        """

        return self.record_result.quality

    @property
    def overall_score(self) -> float:
        return self.record_result.overall_score

    @property
    def summary(self) -> str | None:
        return self.record_result.summary

    @property
    def field_results(self) -> list[FieldComparisonResult] | None:
        return self.record_result.field_results

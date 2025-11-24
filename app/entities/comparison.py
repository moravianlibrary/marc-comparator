from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, List, Optional

from esorm.fields import Keyword, Text
from marc_comparator.comparators import RecordComparisonResult
from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession
from adapters.indexer import IndexerNestedModel

from ._operations import BaseOperationsMixin

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


# --- Indexer Schemas -------------------------------------------------------


class SubfieldComparisonResult(IndexerNestedModel):
    code: Keyword
    score: float
    explanation: Keyword | None = None
    details: Text | None = None


class FieldComparisonResult(IndexerNestedModel):
    tag: Keyword
    score: float
    explanation: Keyword | None = None
    details: Text | None = None
    subfield_results: List[SubfieldComparisonResult] | None = None


class ComparisonSchema(IndexerNestedModel):
    comparator: Keyword

    base: Keyword
    system_number: Keyword

    overall_score: float
    summary: str | None = None
    field_results: List[FieldComparisonResult] | None = None

    updated_at: datetime


# --- Database Model -------------------------------------------------------


class Comparison(Base, BaseOperationsMixin):
    __tablename__ = "comparisons"

    main_record_id = Column(
        String, ForeignKey("catalog_records.id"), primary_key=True
    )
    comparator = Column(String, nullable=False, primary_key=True)
    other_record_id = Column(
        String, ForeignKey("catalog_records.id"), nullable=False
    )

    _result = Column("result", JSONB, nullable=False)
    updated_at = Column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )

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
        other_record_id: str,
    ) -> Optional["Comparison"]:
        return (
            db_session.query(cls)
            .filter_by(
                main_record_id=main_record_id,
                comparator=comparator,
                other_record_id=other_record_id,
            )
            .one_or_none()
        )

    @property
    def base(self) -> str:
        return self.other_record.base

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
        if "record_result" in self.__dict__:
            del self.__dict__["record_result"]

    @cached_property
    def record_result(self) -> RecordComparisonResult:
        return RecordComparisonResult.model_validate(self._result)

    @property
    def overall_score(self) -> float:
        return self.record_result.overall_score

    @property
    def summary(self) -> str | None:
        return self.record_result.summary

    @property
    def field_results(self) -> List[FieldComparisonResult] | None:
        return self.record_result.field_results

from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, List

from esorm.fields import Keyword, Text
from marc_comparator.validators import (
    ValidationResult,
    ValidationTarget,
    Validator,
    ValidityStatus,
)
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession
from adapters.indexer import IndexerNestedModel

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class ValidationTargetSchema(IndexerNestedModel):
    tag: Keyword
    codes: List[Keyword] | None = None


class ValidationSchema(IndexerNestedModel):
    validator: Validator

    target: ValidationTargetSchema
    status: ValidityStatus

    reason: Keyword | None = None
    details: Text | None = None
    hint: Text | None = None

    updated_at: datetime


class Validation(Base):
    __tablename__ = "validations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    catalog_record_id = Column(
        String, ForeignKey("catalog_records.id"), nullable=False
    )
    validator = Column(String, nullable=False)

    _result = Column(JSONB, name="result", nullable=False)
    updated_at = Column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )

    catalog_record: Mapped["CatalogRecord"] = relationship(
        "CatalogRecord",
        foreign_keys=[catalog_record_id],
        back_populates="validations",
        lazy="select",
    )

    # --- CRUD operations ---

    @classmethod
    def save_all(
        cls,
        db_session: DatabaseSession,
        catalog_record_id: str,
        validator: str,
        results: List[ValidationResult],
    ) -> None:
        for result in results:
            db_session.add(
                cls(
                    catalog_record_id=catalog_record_id,
                    validator=validator,
                    result=result.model_dump(),
                )
            )
        db_session.commit()

    @classmethod
    def delete_by_record_and_validator(
        cls,
        db_session: DatabaseSession,
        catalog_record_id: str,
        validator: str,
    ) -> None:
        (
            db_session.query(cls)
            .filter_by(
                catalog_record_id=catalog_record_id,
                validator=validator,
            )
            .delete(synchronize_session=False)
        )
        db_session.commit()

    # --- Properties for accessing validation result ---

    @property
    def result(self) -> dict:
        return self._result

    @result.setter
    def result(self, value: dict):
        self._result = value
        # Invalidate cached property
        if "validation_result" in self.__dict__:
            del self.__dict__["validation_result"]

    @cached_property
    def validation_result(self) -> ValidationResult:
        return ValidationResult.model_validate(self._result)

    @property
    def target(self) -> ValidationTarget:
        return self.validation_result.target

    @property
    def status(self) -> ValidityStatus:
        return self.validation_result.status

    @property
    def reason(self) -> str | None:
        return self.validation_result.reason

    @property
    def details(self) -> str | None:
        return self.validation_result.details

    @property
    def hint(self) -> str | None:
        return self.validation_result.hint

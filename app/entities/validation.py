from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING

from marc_comparator.validators import (
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)
from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.database import Base, DatabaseSession

if TYPE_CHECKING:
    from .catalog_record import CatalogRecord


class Validation(Base):
    __tablename__ = "validations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    catalog_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("catalog_records.id"), index=True
    )
    validator: Mapped[str] = mapped_column(String)

    _result: Mapped[dict] = mapped_column("result", JSONB)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

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
        results: list[ValidationResult],
    ) -> None:
        for result in results:
            db_session.add(
                cls(
                    catalog_record_id=catalog_record_id,
                    validator=validator,
                    result=result.model_dump(),
                )
            )
        db_session.flush()

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
        db_session.flush()

    # --- Properties for accessing validation result ---

    @property
    def result(self) -> dict:
        return self._result

    @result.setter
    def result(self, value: dict):
        self._result = value
        # Invalidate cached property
        vars(self).pop("validation_result", None)

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
    def params(self) -> dict | None:
        return self.validation_result.params

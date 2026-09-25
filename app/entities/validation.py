from collections.abc import Iterable, Sequence
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


def _fingerprint(results: Iterable[ValidationResult]) -> list[str]:
    """A comparable form of one record's results for a validator.

    Sorted, because the stored rows come back in whatever order the database
    finds them and a different order is not a different answer. Compared
    through the model rather than as raw JSON so that a stored row which omits
    a field the model defaults reads as the answer it parses to, instead of as
    a change worth rewriting.
    """

    return sorted(result.model_dump_json() for result in results)


def stored_results_for(
    db_session: DatabaseSession, record_ids: Sequence[str]
) -> dict[tuple[str, str], list[ValidationResult]]:
    """What is stored for a window of records, keyed by (record, validator).

    One query for the window in place of one per record per validator, which
    is what ``replace_all`` otherwise costs to find out that it has nothing
    to do.
    """

    wanted = list(record_ids)
    stored: dict[tuple[str, str], list[ValidationResult]] = {}
    if not wanted:
        return stored
    for row in db_session.query(Validation).filter(Validation.catalog_record_id.in_(wanted)).all():
        stored.setdefault((row.catalog_record_id, row.validator), []).append(row.validation_result)
    return stored


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
    def replace_all(
        cls,
        db_session: DatabaseSession,
        catalog_record_id: str,
        validator: str,
        results: list[ValidationResult],
        existing: Sequence[ValidationResult] | None = None,
    ) -> bool:
        """Store these results, leaving the rows alone if they already say this.

        Every pass used to delete a record's validations and write the same
        ones straight back, for every record, whether or not the validator had
        found anything different — measured at 3239 deletes and 3207 inserts
        for 472 rows that actually changed. Reading them first replaces that
        with one query, and on a pass that changes nothing it is the only
        statement issued.

        Callers walking a window already know what is stored for every record
        in it and can hand that in; the rest pay one query to find out.

        Returns whether anything was written.
        """
        if existing is None:
            existing = [
                row.validation_result
                for row in db_session.query(cls)
                .filter_by(catalog_record_id=catalog_record_id, validator=validator)
                .all()
            ]
        if _fingerprint(existing) == _fingerprint(results):
            return False

        cls.delete_by_record_and_validator(db_session, catalog_record_id, validator)
        cls.save_all(db_session, catalog_record_id, validator, results)
        return True

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

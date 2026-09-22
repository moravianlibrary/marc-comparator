from abc import ABC, abstractmethod
from collections.abc import Iterable
from enum import StrEnum

from marcdantic import MarcRecord
from pydantic import BaseModel

from ..harvest import HarvestCapable
from ..reports import ReportFile


class ValidityStatus(StrEnum):
    Valid = "Valid"
    ForReview = "ForReview"
    Invalid = "Invalid"
    AdditionalInfo = "AdditionalInfo"


class ValidationTarget(BaseModel):
    tag: str
    codes: list[str] | None = None
    field_index: int | None = None


class ValidationResult(BaseModel):
    """
    Single result of validating a MARC record.

    Attributes:
        status: The validity status (e.g., Valid, Invalid).
        target: The field in the MARC record that was validated.
        reason: Identifier key for the validation result.
        params: Contextual parameters associated with the result.
    """

    target: ValidationTarget
    status: ValidityStatus

    reason: str | None = None
    params: dict[str, str] | None = None


class ReportInput(BaseModel):
    """One record's not-valid results plus its full MARC, for report building."""

    catalog_record_id: str
    base: str
    marc: MarcRecord
    results: list[ValidationResult]


class BaseValidator(HarvestCapable, ABC):
    """Abstract base class for MARC record validators."""

    config_model: type[BaseModel] | None = None

    #: Whether this validator can turn its stored not-valid results into a
    #: downloadable repair artifact. Validators that can override
    #: ``generate_report`` set this True.
    can_generate_report: bool = False

    def __init__(self, config: BaseModel | None = None) -> None:
        #: Validators declaring a ``config_model`` are constructed with an
        #: instance of it; the rest take no config at all.
        self.config = config

    @abstractmethod
    async def run(self, record: MarcRecord) -> list[ValidationResult]:
        """
        Validate a MARC record and return a list of validation results.
        """
        raise NotImplementedError

    def generate_report(self, records: Iterable[ReportInput]) -> list[ReportFile]:
        """
        Build repair-artifact files from not-valid results.

        Override in validators that support it. Pure/CPU-only: no network, no
        DB — takes MARC + results, returns file bytes, so it is unit-testable
        against fixtures.
        """
        raise NotImplementedError

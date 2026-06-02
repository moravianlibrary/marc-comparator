from abc import ABC, abstractmethod
from enum import StrEnum

from marcdantic import MarcRecord
from pydantic import BaseModel


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


class BaseValidator(ABC):
    """Abstract base class for MARC record validators."""

    config_model: type[BaseModel] | None = None

    @abstractmethod
    async def run(self, record: MarcRecord) -> list[ValidationResult]:
        """
        Validate a MARC record and return a list of validation results.
        """
        raise NotImplementedError

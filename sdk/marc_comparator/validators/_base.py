from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Dict, List

from marcdantic import MarcRecord
from pydantic import BaseModel


class ValidityStatus(StrEnum):
    Valid = "Valid"
    ForReview = "ForReview"
    Invalid = "Invalid"
    AdditionalInfo = "AdditionalInfo"


class ValidationTarget(BaseModel):
    tag: str
    codes: List[str] | None = None
    field_index: int | None = None


class ValidationResult(BaseModel):
    """
    Single result of validating a MARC record.

    Attributes:
        status: The validity status (e.g., Valid, Invalid).
        target: The field in the MARC record that was validated.
        reason: A short reason for the validation result.
        details: Optional additional context or data.
        hint: Optional guidance for fixing the issue.
    """

    target: ValidationTarget
    status: ValidityStatus

    reason: str | None = None
    details: str | None = None
    details_params: Dict[str, str] | None = None
    hint: str | None = None


class BaseValidator(ABC):
    """Abstract base class for MARC record validators."""

    config_model: type[BaseModel] | None = None

    @abstractmethod
    async def run(self, record: MarcRecord) -> List[ValidationResult]:
        """
        Validate a MARC record and return a list of validation results.
        """
        raise NotImplementedError

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import List

from marcdantic import MarcRecord
from pydantic import BaseModel


class ValidityStatus(StrEnum):
    Valid = "Valid"
    Invalid = "Invalid"
    Warning = "Warning"
    Info = "Info"


@dataclass
class ValidationTarget:
    tag: str
    codes: List[str] | None = None


@dataclass
class ValidationResult:
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

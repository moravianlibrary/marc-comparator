from enum import StrEnum

from ..reports import ReportFile
from ._base import (
    BaseValidator,
    ReportInput,
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)
from .kramerius_links import (
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)


class Validator(StrEnum):
    KrameriusLinks = "kramerius-links"


VALIDATOR_DISPATCHER: dict[Validator, type[BaseValidator]] = {
    Validator.KrameriusLinks: KrameriusLinksValidator,
}

__all__ = [
    "BaseValidator",
    "KrameriusLinksValidator",
    "KrameriusLinksValidatorConfig",
    "ReportFile",
    "ReportInput",
    "VALIDATOR_DISPATCHER",
    "ValidationResult",
    "ValidationTarget",
    "Validator",
    "ValidityStatus",
]

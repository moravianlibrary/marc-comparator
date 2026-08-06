from enum import StrEnum

from ..reports import ReportFile
from ._base import (
    BaseComparator,
    ComparisonReportInput,
    Explanation,
    FieldComparisonResult,
    MatchQuality,
    RecordComparisonResult,
    SubfieldComparisonResult,
)
from .default import DefaultComparator, DefaultComparatorConfig


class Comparator(StrEnum):
    Default = "default"


COMPARATOR_DISPATCHER: dict[Comparator, type[BaseComparator]] = {
    Comparator.Default: DefaultComparator,
}

__all__ = [
    "BaseComparator",
    "COMPARATOR_DISPATCHER",
    "Comparator",
    "ComparisonReportInput",
    "DefaultComparator",
    "DefaultComparatorConfig",
    "Explanation",
    "FieldComparisonResult",
    "MatchQuality",
    "RecordComparisonResult",
    "ReportFile",
    "SubfieldComparisonResult",
]

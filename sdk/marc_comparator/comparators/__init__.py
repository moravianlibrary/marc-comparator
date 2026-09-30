from enum import StrEnum

from ..reports import ReportFile
from ._base import (
    EXCELLENT_MATCH,
    MATCH_SCALE,
    MATCH_SCALE_MAX,
    MODERATE_MATCH,
    BaseComparator,
    ComparisonReportInput,
    Explanation,
    FieldComparisonResult,
    MatchQuality,
    RecordComparisonResult,
    SubfieldComparisonResult,
    match_from_penalty,
)
from .default import DefaultComparator, DefaultComparatorConfig


class Comparator(StrEnum):
    Default = "default"


COMPARATOR_DISPATCHER: dict[Comparator, type[BaseComparator]] = {
    Comparator.Default: DefaultComparator,
}

__all__ = [
    "BaseComparator",
    "EXCELLENT_MATCH",
    "MATCH_SCALE",
    "MATCH_SCALE_MAX",
    "MODERATE_MATCH",
    "match_from_penalty",
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

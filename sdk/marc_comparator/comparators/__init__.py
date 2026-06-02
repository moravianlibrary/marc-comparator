from enum import StrEnum

from ._base import (
    BaseComparator,
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
    "DefaultComparator",
    "DefaultComparatorConfig",
    "Explanation",
    "FieldComparisonResult",
    "MatchQuality",
    "RecordComparisonResult",
    "SubfieldComparisonResult",
]

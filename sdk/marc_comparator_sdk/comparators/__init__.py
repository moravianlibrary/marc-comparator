from enum import StrEnum
from typing import Type

from ._base import (
    BaseComparator,
    FieldComparisonResult,
    RecordComparisonResult,
    SubfieldComparisonResult,
)
from .rule_based import RuleBasedComparator, RuleBasedComparatorConfig


class Comparator(StrEnum):
    RuleBased = "rule-based"


COMPARATOR_DISPATCHER: dict[Comparator, Type[BaseComparator]] = {
    Comparator.RuleBased: RuleBasedComparator,
}

__all__ = [
    "BaseComparator",
    "COMPARATOR_DISPATCHER",
    "Comparator",
    "FieldComparisonResult",
    "RecordComparisonResult",
    "RuleBasedComparator",
    "RuleBasedComparatorConfig",
    "SubfieldComparisonResult",
]

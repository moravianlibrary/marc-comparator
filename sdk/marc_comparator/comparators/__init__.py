from enum import StrEnum
from typing import Type

from ._base import (
    BaseComparator,
    FieldComparisonResult,
    RecordComparisonResult,
    SubfieldComparisonResult,
)
from .intiim import IntiimComparator, IntiimComparatorConfig


class Comparator(StrEnum):
    Intiim = "intiim"


COMPARATOR_DISPATCHER: dict[Comparator, Type[BaseComparator]] = {
    Comparator.Intiim: IntiimComparator,
}

__all__ = [
    "BaseComparator",
    "COMPARATOR_DISPATCHER",
    "Comparator",
    "FieldComparisonResult",
    "IntiimComparator",
    "IntiimComparatorConfig",
    "RecordComparisonResult",
    "SubfieldComparisonResult",
]

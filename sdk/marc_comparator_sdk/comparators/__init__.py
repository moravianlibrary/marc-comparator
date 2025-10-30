from enum import StrEnum
from typing import Type

from ._base import BaseComparator
from .rule_based import RuleBasedComparator


class Comparator(StrEnum):
    RuleBased = "rule-based"


COMPARATOR_DISPATCHER: dict[Comparator, Type[BaseComparator]] = {
    Comparator.RuleBased: RuleBasedComparator,
}

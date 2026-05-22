# The comparator the app uses. Change these to switch implementations.
from marc_comparator.comparators import Comparator as _Comparator
from marc_comparator.comparators import DefaultComparator, DefaultComparatorConfig

UsedComparator = _Comparator.Default
UsedComparatorClass = DefaultComparator
UsedComparatorConfig = DefaultComparatorConfig

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from marcdantic import MarcRecord
from pydantic import BaseModel


@dataclass()
class SubfieldComparison:
    """
    Represents a target for comparison within a MARC subfield.

    Attributes
    ----------
    code: str
        The MARC subfield code being compared.
    score: float
        The similarity score for this subfield (0.0 to 1.0).
    explanation: str | None
        An optional explanation explaining the score.
    details: str | None
        Optional additional details about the comparison.
    """

    code: str
    score: float
    explanation: str | None = None
    details: str | None = None


@dataclass(slots=True)
class FieldComparison:
    """
    Represents a target for comparison within a MARC record.

    Attributes
    ----------
    tag: str
        The MARC field tag being compared.
    codes: List[str] | None
        Specific subfield codes within the tag being compared.
    score: float
        The similarity score for this field (0.0 to 1.0).
    explanation: str | None
        An optional explanation explaining the score.
    """

    tag: str
    score: float
    explanation: str | None = None
    subtargets: List[SubfieldComparison] | None = None


@dataclass(slots=True)
class RecordComparison:
    """
    Represents the result of comparing two MARC records.

    Attributes
    ----------
    overall_score: float
        The overall similarity score between the two records (0.0 to 1.0).
    summary: str | None
        An optional summary of the comparison results.
    targets: List[FieldComparison]
        A list of detailed comparison results for individual targets.

    """

    overall_score: float
    summary: str | None = None
    targets: List[FieldComparison] | None = None


class BaseComparator(ABC):
    """Abstract base class for MARC record comparators."""

    config_model: type[BaseModel] | None = None

    @abstractmethod
    async def run(
        self,
        record_a: MarcRecord,
        record_b: MarcRecord,
    ) -> RecordComparison:
        """
        Compare two MARC records and return a RecordComparison.

        Parameters
        ----------
        record_a : MarcRecord
            The first MARC record to compare.
        record_b : MarcRecord
            The second MARC record to compare.
        """
        pass

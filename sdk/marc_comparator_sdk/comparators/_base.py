from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from marcdantic import MarcRecord
from pydantic import BaseModel


@dataclass
class SubfieldComparisonResult:
    """
    Represents the result of comparing a MARC subfield.

    Attributes
    ----------
    code: str
        The MARC subfield code being compared.
    score: float
        The similarity score for this subfield.
    explanation: str | None
        Optional explanation describing the score.
    details: str | None
        Optional additional details about the comparison.
    """

    code: str
    score: float
    explanation: str | None = None
    details: str | None = None


@dataclass(slots=True)
class FieldComparisonResult:
    """
    Represents the result of comparing a MARC field.

    Attributes
    ----------
    tag: str
        The MARC field tag being compared.
    score: float
        The similarity score for this field (0.0 to 1.0).
    explanation: str | None
        Optional explanation describing the score.
    details: str | None
        Optional additional details about the comparison.
    subfield_results: List[SubfieldResult] | None
        Detailed comparison results for subfields within this field.
    """

    tag: str
    score: float
    explanation: str | None = None
    details: str | None = None
    subfield_results: List[SubfieldComparisonResult] | None = None


@dataclass(slots=True)
class RecordComparisonResult:
    """
    Represents the result of comparing two MARC records.

    Attributes
    ----------
    overall_score: float
        The overall similarity score between the two records (0.0 to 1.0).
    summary: str | None
        Optional summary of the comparison results.
    field_results: List[FieldResult] | None
        Detailed comparison results for individual fields.
    """

    overall_score: float
    summary: str | None = None
    field_results: List[FieldComparisonResult] | None = None


class BaseComparator(ABC):
    """Abstract base class for MARC record comparators."""

    config_model: type[BaseModel] | None = None

    @abstractmethod
    async def run(
        self,
        record_a: MarcRecord,
        record_b: MarcRecord,
    ) -> RecordComparisonResult:
        """
        Compare two MARC records and return a RecordComparisonResult.

        Parameters
        ----------
        record_a : MarcRecord
            The first MARC record to compare.
        record_b : MarcRecord
            The second MARC record to compare.
        """
        pass

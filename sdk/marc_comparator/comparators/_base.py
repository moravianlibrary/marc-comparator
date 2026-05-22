from abc import ABC, abstractmethod
from enum import StrEnum
from typing import List

from marcdantic import MarcRecord
from pydantic import BaseModel


class MatchQuality(StrEnum):
    """
    Enum representing the quality of a match between MARC records.

    Attributes
    ----------
    Excellent : str
        Indicates an excellent match.
        Score range: 0.9 - 1.0.
    Moderate : str
        Indicates a moderate match.
        Score range: 0.7 - 0.9.
    Poor : str
        Indicates a poor match.
        Score range: 0.0 - 0.7.
    """

    Excellent = "Excellent"
    Moderate = "Moderate"
    Poor = "Poor"


class Explanation(StrEnum):
    """Classification of a field/subfield comparison result."""

    Identical = "Identical"
    NonStandardized = "NonStandardized"
    Typo = "Typo"
    Incomplete = "Incomplete"
    Incorrect = "Incorrect"
    Missing = "Missing"


class SubfieldComparisonResult(BaseModel):
    """
    Represents the result of comparing a MARC subfield.

    Attributes
    ----------
    code: str
        The MARC subfield code being compared.
    idxA: int | None
        The index of the subfield in record A, if applicable.
    idxB: int | None
        The index of the subfield in record B, if applicable.
    score: float
        The similarity score for this subfield.
    explanation: Explanation | None
        Classification of the comparison result.
    details: str | None
        Optional additional details about the comparison.
    """

    code: str
    idxA: int | None = None
    idxB: int | None = None
    value_a: str | None = None
    value_b: str | None = None
    score: float
    explanation: Explanation | None = None
    details: str | None = None


class FieldComparisonResult(BaseModel):
    """
    Represents the result of comparing a MARC field.

    Attributes
    ----------
    tag: str
        The MARC field tag being compared.
    tagB: str | None
        The MARC field tag in record B, if different.
    idxA: int | None
        The index of the field in record A, if applicable.
    idxB: int | None
        The index of the field in record B, if applicable.
    score: float
        The similarity score for this field.
    explanation: Explanation | None
        Classification of the comparison result.
    details: str | None
        Optional additional details about the comparison.
    subfield_results: List[SubfieldComparisonResult] | None
        Detailed comparison results for subfields within this field.
    """

    tag: str
    tagB: str | None = None
    idxA: int | None = None
    idxB: int | None = None
    score: float
    explanation: Explanation | None = None
    details: str | None = None
    subfield_results: List[SubfieldComparisonResult] | None = None


class RecordComparisonResult(BaseModel):
    """
    Represents the result of comparing two MARC records.

    Attributes
    ----------
    overall_score: float
        The overall similarity score between the two records.
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

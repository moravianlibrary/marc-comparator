import csv
import io
from abc import ABC, abstractmethod
from collections.abc import Iterable
from enum import StrEnum

from marcdantic import MarcRecord
from pydantic import BaseModel

from ..reports import ReportFile


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
    value_a: str | None = None
    value_b: str | None = None
    score: float
    explanation: Explanation | None = None
    details: str | None = None
    subfield_results: list[SubfieldComparisonResult] | None = None


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
    field_results: list[FieldComparisonResult] | None = None


class ComparisonReportInput(BaseModel):
    """One stored comparison, for building a refinement report."""

    catalog_record_id: str
    base: str
    other_record_id: str
    result: RecordComparisonResult


_REPORT_COLUMNS = [
    "catalog_record_id",
    "base",
    "other_record_id",
    "overall_score",
    "field_tag",
    "subfield_code",
    "value_a",
    "value_b",
    "score",
    "explanation",
    "details",
]


class BaseComparator(ABC):
    """Abstract base class for MARC record comparators."""

    config_model: type[BaseModel] | None = None

    #: Whether this comparator can turn its stored results into a downloadable
    #: analysis report. The generic CSV implementation below works for any
    #: comparator, so this is on by default.
    can_generate_report: bool = True

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

    def generate_report(
        self, comparisons: Iterable[ComparisonReportInput]
    ) -> list[ReportFile]:
        """
        Build a flat CSV analysis report from stored comparison results.

        One row per compared subfield (or per field when it has no subfield
        results): field tag, the two values, the score, and the ``Explanation``
        classification — so a human can spot where the comparator misjudges and
        tune the config/model. Pure/CPU-only: no network, no DB.
        """
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_REPORT_COLUMNS)
        writer.writeheader()

        for item in comparisons:
            base_row = {
                "catalog_record_id": item.catalog_record_id,
                "base": item.base,
                "other_record_id": item.other_record_id,
                "overall_score": item.result.overall_score,
            }
            for field in item.result.field_results or []:
                subfields = field.subfield_results or []
                if subfields:
                    for sub in subfields:
                        writer.writerow(
                            {
                                **base_row,
                                "field_tag": field.tag,
                                "subfield_code": sub.code,
                                "value_a": sub.value_a,
                                "value_b": sub.value_b,
                                "score": sub.score,
                                "explanation": sub.explanation,
                                "details": sub.details,
                            }
                        )
                else:
                    writer.writerow(
                        {
                            **base_row,
                            "field_tag": field.tag,
                            "subfield_code": None,
                            "value_a": field.value_a,
                            "value_b": field.value_b,
                            "score": field.score,
                            "explanation": field.explanation,
                            "details": field.details,
                        }
                    )

        return [
            ReportFile(
                filename="comparator_report.csv",
                content=buffer.getvalue().encode("utf-8"),
                content_type="text/csv",
            )
        ]

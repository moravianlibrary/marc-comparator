import csv
import io
from abc import ABC, abstractmethod
from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from marcdantic import MarcRecord
from pydantic import BaseModel, model_validator

from ..reports import ReportFile

#: The top of the match scale: two records the comparator found nothing to
#: separate. Scores run 0 to 15, bigger is better, and the number is a
#: re-expression of the scoring engine's own output rather than a curve laid
#: over it — see ``MATCH_SCALE`` below.
MATCH_SCALE_MAX = 15.0

#: The engine scores a *penalty* from 0 to ``RECORD_CAP`` (30), bigger meaning
#: further apart. A match score is that penalty turned the right way up and
#: halved, so the two scales are one affine map apart and nothing is lost:
#:
#:     match = MATCH_SCALE_MAX - penalty / 2
#:
#: Halving is what puts 0-30 onto 0-15; the direction flip is what makes the
#: number answer "how good is this match" instead of "how bad".
MATCH_SCALE = "match15"

#: A match at least this good is Excellent — the engine's penalty 6 or less.
EXCELLENT_MATCH = 12.0

#: A match at least this good is Moderate — the engine's penalty 12 or less.
MODERATE_MATCH = 9.0


def match_from_penalty(penalty: float) -> float:
    """Turn the engine's 0-30 penalty into a 0-15 match score."""

    return MATCH_SCALE_MAX - penalty / 2.0


class MatchQuality(StrEnum):
    """
    Enum representing the quality of a match between MARC records.

    Attributes
    ----------
    Excellent : str
        Indicates an excellent match.
        Score range: 12 - 15.
    Moderate : str
        Indicates a moderate match.
        Score range: 9 - 12.
    Poor : str
        Indicates a poor match.
        Score range: 0 - 9.
    """

    Excellent = "Excellent"
    Moderate = "Moderate"
    Poor = "Poor"

    @classmethod
    def of(
        cls,
        score: float,
        *,
        excellent: float = EXCELLENT_MATCH,
        moderate: float = MODERATE_MATCH,
    ) -> "MatchQuality":
        """Which band a match score falls in.

        The one place the bands are applied. They used to be written out again
        in the entity that stores a comparison and a third time in the
        analytics SQL, as three copies of the same two literals that nothing
        kept in step.
        """

        if score >= excellent:
            return cls.Excellent
        if score >= moderate:
            return cls.Moderate
        return cls.Poor


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
        How good this subfield's match is, 0 to 15, on the same scale as the
        record score and derived from the same arithmetic.
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
        How good this field's match is, 0 to 15, on the same scale as the
        record score and derived from the same arithmetic.
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
        How good the match is, 0 to 15, bigger is better.
    quality: MatchQuality
        Which band ``overall_score`` falls in, decided once here so that
        everything downstream reads the same answer.
    scale: str
        Which scale ``overall_score`` and every nested score are on. Stored
        results are read back long after they were written, and the scale this
        carries has changed once already — from a 0-1 similarity to the 0-15
        match score. The two ranges overlap, so a stale row cannot be told from
        a current one by its value alone. This is how it is told.
    summary: str | None
        Optional summary of the comparison results.
    field_results: List[FieldResult] | None
        Detailed comparison results for individual fields.
    """

    overall_score: float
    #: The default is unreachable: ``overall_score`` is required, so the
    #: validator below always has something to band and always replaces it.
    #: It is here so that a caller building a result by hand does not have to
    #: repeat an answer this class can work out.
    quality: MatchQuality = MatchQuality.Poor
    scale: str = MATCH_SCALE
    summary: str | None = None
    field_results: list[FieldComparisonResult] | None = None

    @model_validator(mode="before")
    @classmethod
    def _band_the_score(cls, data: Any) -> Any:
        """Fill in ``quality`` from ``overall_score`` when nobody said.

        A comparator with thresholds of its own passes the band it decided on;
        everyone else — a caller building a result by hand, a stored row from
        before the field existed — gets the default bands rather than having
        to repeat them.
        """

        if isinstance(data, dict) and data.get("quality") is None and "overall_score" in data:
            return {**data, "quality": MatchQuality.of(float(data["overall_score"]))}
        return data


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

    def __init__(self, config: BaseModel | None = None) -> None:
        #: Comparators declaring a ``config_model`` are constructed with an
        #: instance of it; the rest take no config at all.
        self.config = config

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

    def generate_report(self, comparisons: Iterable[ComparisonReportInput]) -> list[ReportFile]:
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

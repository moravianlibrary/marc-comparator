from enum import StrEnum

from pydantic import BaseModel

from catalog_records.models import RecordFilter


class ReportToolKind(StrEnum):
    Validator = "validator"
    Comparator = "comparator"


class CreateReportData(BaseModel):
    """Request/task payload for generating a report.

    ``tool`` is the validator or comparator enum value (e.g. ``kramerius-links``
    or ``default``); ``kind`` selects which registry it comes from.
    """

    kind: ReportToolKind
    tool: str
    filters: RecordFilter = RecordFilter()

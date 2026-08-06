from pydantic import BaseModel


class ReportFile(BaseModel):
    """A single file produced by a report.

    Bundled into a downloadable archive by the app. The content is raw bytes so
    text (e.g. Aleph ``.seq``) and binary (e.g. XLSX) files share one type.
    """

    filename: str
    content: bytes
    content_type: str = "text/plain"

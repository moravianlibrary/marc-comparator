from datetime import datetime
from typing import List, Literal

from aleph_nought import AlephOAIConfig
from marc_comparator.authority_linkers import AuthorityLinker
from marc_comparator.comparators import Comparator, MatchQuality
from marc_comparator.validators import Validator, ValidityStatus
from pydantic import BaseModel, Field

from entities.settings import SettingsSchema


class CatalogSettings(SettingsSchema):
    clients: List[AlephOAIConfig] = [
        AlephOAIConfig(
            base="MZK01",
            host="https://aleph.mzk.cz",
            endpoint="OAI",
            system_number_pattern=r"\d{9}",
            oai_sets=["MZK01-VDK"],
            oai_identifier_template="oai:aleph.mzk.cz:{base}-{doc_number}",
        )
    ]


class FetchRecordData(BaseModel):
    base: str
    system_number: str


class FetchBaseRecordsData(BaseModel):
    base: str
    system_numbers: List[str]


class FetchBatchOfRecordsData(BaseModel):
    per_base: List[FetchBaseRecordsData]


class SyncRecordsData(BaseModel):
    base: str
    from_date: datetime | None = None


class RecordFilter(BaseModel):
    text_query: str | None = None

    # Scalar
    bases: list[str] | None = None
    type_of_record: list[str] | None = None
    bibliographic_level: list[str] | None = None

    # Boolean
    hidden: bool | None = None
    deleted: bool | None = None
    processed: bool | None = None

    # Relationship
    authority_link_linkers: list[str] | None = None
    authority_link_bases: list[str] | None = None
    comparators: list[str] | None = None
    comparison_bases: list[str] | None = None
    match_qualities: list[str] | None = None
    field_explanations: list[str] | None = None
    validators: list[str] | None = None
    validation_statuses: list[str] | None = None
    validation_target_tags: list[str] | None = None

    # Score range
    score_min: float | None = None
    score_max: float | None = None


class SetRecordsVisibilityData(BaseModel):
    filters: RecordFilter = RecordFilter()
    visible: bool = False


class ProcessRecordsSettings(SettingsSchema):
    target_bases: List[str] = Field(
        default=["MZK01"], min_length=1
    )
    authority_linkers: List[AuthorityLinker] = Field(
        default=[AuthorityLinker.KnihovnyCz], min_length=1
    )
    comparator: Comparator = Field(default=Comparator.Intiim)
    validators: List[Validator] = Field(
        default=[Validator.KrameriusLinks], min_length=1
    )


class SearchRecordsRequest(BaseModel):
    filters: RecordFilter = RecordFilter()
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    sort_by: Literal["id", "base", "system_number", "latest_sync", "updated_at"] = "id"
    sort_order: Literal["asc", "desc"] = "asc"


class AuthorityLinkSummary(BaseModel):
    linker: str
    base: str
    authority_record_id: str


class ComparisonSummary(BaseModel):
    comparator: str
    base: str
    other_record_id: str
    overall_score: float
    match_quality: MatchQuality


class ValidationSummary(BaseModel):
    validator: str
    target_tag: str
    status: ValidityStatus


class RecordSummary(BaseModel):
    id: str
    base: str
    system_number: str
    title: str | None = None
    authors: list[str] = []
    state: list[str] = []
    authority_links: list[AuthorityLinkSummary] = []
    comparisons: list[ComparisonSummary] = []
    validations: list[ValidationSummary] = []
    latest_sync: datetime | None = None
    latest_transaction: datetime | None = None
    processed_at: datetime | None = None


class SearchRecordsResponse(BaseModel):
    items: list[RecordSummary]
    total: int
    page: int
    page_size: int


class FacetsRequest(BaseModel):
    filters: RecordFilter = RecordFilter()


class FacetBucket(BaseModel):
    key: str
    count: int


class FacetResult(BaseModel):
    field: str
    buckets: list[FacetBucket]


class HistogramBucket(BaseModel):
    min: float
    max: float
    count: int


class HistogramResult(BaseModel):
    field: str
    buckets: list[HistogramBucket]


class FacetsResponse(BaseModel):
    facets: list[FacetResult]
    histograms: list[HistogramResult]
    total: int


class FacetsPreviewRequest(BaseModel):
    filters: RecordFilter = RecordFilter()
    target_field: str


class FacetsPreviewEntry(BaseModel):
    """Facet distributions for all OTHER fields when target_field == target_value."""
    target_value: str
    facets: list[FacetResult]
    histograms: list[HistogramResult]
    total: int


class FacetsPreviewResponse(BaseModel):
    target_field: str
    previews: list[FacetsPreviewEntry]

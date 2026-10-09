from datetime import datetime
from typing import Literal

from aleph_nought import AlephOAIConfig
from marc_comparator.authority_linkers import AuthorityLinker
from marc_comparator.comparators import MatchQuality
from marc_comparator.validators import Validator, ValidityStatus
from pydantic import BaseModel, Field

from entities.settings import SettingsSchema


def _mzk_oai_client(base: str) -> AlephOAIConfig:
    """MZK's Aleph bases are served by one OAI endpoint and differ only in the
    base code and the name of its digitised-documents set."""
    return AlephOAIConfig(
        base=base,
        host="https://aleph.mzk.cz",
        endpoint="OAI",
        system_number_pattern=r"\d{9}",
        oai_sets=[f"{base}-VDK"],
        # {base} and {doc_number} are filled in per record, not here.
        oai_identifier_template="oai:aleph.mzk.cz:{base}-{doc_number}",
    )


class CatalogSettings(SettingsSchema):
    clients: list[AlephOAIConfig] = [_mzk_oai_client("MZK01"), _mzk_oai_client("MZK03")]
    kramerius_client_urls: dict[str, str] = {}


class FetchRecordData(BaseModel):
    base: str
    system_number: str


class FetchBaseRecordsData(BaseModel):
    base: str
    system_numbers: list[str]


class FetchBatchOfRecordsData(BaseModel):
    per_base: list[FetchBaseRecordsData]


class SyncRecordsData(BaseModel):
    base: str
    from_date: datetime | None = None


class RecordFilter(BaseModel):
    record_ids: list[str] | None = None
    text_query: str | None = None

    # Scalar
    bases: list[str] | None = None
    type_of_record: list[str] | None = None
    bibliographic_level: list[str] | None = None

    # Boolean
    deleted: bool | None = None
    processed: bool | None = None
    #: True selects only records the last pass could not read, false only those
    #: it could. Separate from `processed`, which a broken record also fails —
    #: "not reached yet" and "cannot be read" are not the same work item.
    broken: bool | None = None
    #: True selects records where linking kept a runner-up behind its answer.
    #: Those are the records where there was a choice to make, which is where
    #: a second opinion is worth anybody's time.
    has_alternatives: bool | None = None
    #: True selects records a cataloguer has ruled on. Their answer stands
    #: whatever the linker now computes, so a reader needs to know which
    #: answers are a person's before arguing with one.
    has_claim: bool | None = None
    #: True selects claims the evidence has since moved against. The claim
    #: still decides the answer; this is the queue of ones worth re-reading.
    claim_needs_review: bool | None = None

    # Review status
    review_statuses: list[str] | None = None

    # Relationship
    authority_link_linkers: list[str] | None = None
    authority_link_bases: list[str] | None = None
    #: What came of trying to link — see `LinkOutcome`. Selects on every
    #: attempt, not only the ones that produced a link, so `NoCandidate` and
    #: `LookupFailed` are as findable as `Linked` is.
    link_outcomes: list[str] | None = None
    link_agencies: list[str] | None = None
    #: Which identifier retrieved an attempt — `cnb`, `isbn`, `issn`, `oclc`,
    #: `uuid`. A low score means opposite things for the first and the last.
    link_identifiers: list[str] | None = None
    comparison_bases: list[str] | None = None
    match_qualities: list[str] | None = None
    field_explanations: list[str] | None = None
    validators: list[str] | None = None
    validation_statuses: list[str] | None = None
    validation_target_tags: list[str] | None = None
    validation_reasons: list[str] | None = None

    # Score range
    score_min: float | None = None
    score_max: float | None = None


class CreateReviewRequest(BaseModel):
    aspect_name: str
    note: str | None = None


class ReviewResponse(BaseModel):
    id: str
    record_id: str
    aspect_name: str
    note: str | None
    reviewed_by: str
    reviewer_name: str | None = None
    reviewed_at: datetime
    status: str


class RecordReviewsResponse(BaseModel):
    current: list[ReviewResponse]
    history: list[ReviewResponse]


class ProcessRecordsSettings(SettingsSchema):
    # SKC is the only base either linker advertises as a target — linking
    # MZK01 against itself is rejected by the same-base guard anyway.
    target_bases: list[str] = Field(default=["SKC"], min_length=1)
    #: Order is priority: linking asks these in turn and stops at the first
    #: answer confident enough, so the list is a sequence and not a set.
    #: The dump linker leads because it answers from an indexed local copy
    #: and settles the large majority of records; knihovny.cz costs one or
    #: two HTTP calls against a service we do not run, so it is worth asking
    #: only for what the dump could not place. It was missing from this
    #: default until now — it was added after the default was written, and
    #: the omission meant a fully harvested install linked a fraction of a
    #: percent of its records and said `NoCandidate` to the rest.
    authority_linkers: list[AuthorityLinker] = Field(
        default=[AuthorityLinker.MarcXmlDump, AuthorityLinker.KnihovnyCz], min_length=1
    )
    validators: list[Validator] = Field(default=[Validator.KrameriusLinks], min_length=1)


class SearchRecordsRequest(BaseModel):
    filters: RecordFilter = RecordFilter()
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    sort_by: Literal[
        "id", "base", "system_number", "latest_sync", "updated_at", "comparison_score"
    ] = "id"
    sort_order: Literal["asc", "desc"] = "asc"


class AuthorityLinkSummary(BaseModel):
    """An accepted link: these two records describe the same work."""

    linker: str
    base: str
    authority_record_id: str
    #: How sure the linker was. Linkers that resolve an identifier report 1.0;
    #: ones that score a match report what they measured, and anything below
    #: certainty is worth showing rather than hiding behind an ordinary link.
    confidence: float | None = None
    #: What found the record: "identifier", "title" or "dedup". This is what
    #: makes a low confidence mean something — two records that agree on an
    #: ISBN and disagree about everything else are a cataloguing difference
    #: worth reviewing, not a doubtful link.
    matched_by: str | None = None


class LinkAttemptSummary(BaseModel):
    """One row of what came of trying to link this record to one base.

    Wider than `AuthorityLinkSummary` and kept beside it rather than folded
    into it: every reader of that one means "the same work", and most of
    these are not. The accepted link appears in both — once as the link it
    is, once as the first entry in the story of how it was chosen.
    """

    base: str
    #: Position in this record's list for the base. 0 is the answer, whatever
    #: it says; anything above is a runner-up it was chosen over.
    rank: int
    #: Linked, Rejected, BelowFloor, NoCandidate or LookupFailed.
    outcome: str
    #: Null where no linker owns the row — every one of them was asked and
    #: none of them answered.
    linker: str | None = None
    #: Set only on the accepted link. A candidate is identified by its natural
    #: key below; persisting a copy of a record nobody chose costs 189 ms and
    #: buys nothing.
    authority_record_id: str | None = None
    authority_base: str | None = None
    authority_sysno: str | None = None
    confidence: float | None = None
    matched_by: str | None = None
    #: Which identifier found it, where an identifier did. The route alone
    #: cannot be read: a pair sharing a national bibliography number and a
    #: pair sharing an ISSN are both "found by identifier", and a low score
    #: means opposite things for the two.
    matched_identifier: str | None = None
    #: How many candidates were weighed in total, on the answer row. Not
    #: derivable from the rows: an unambiguous winner keeps no runner-ups, so
    #: without this "one candidate" and "eight, seven of them pruned" look
    #: the same.
    candidate_count: int | None = None
    #: Why, for an outcome that has something to explain — the error text of
    #: a lookup that never completed, and nothing for the rest.
    detail: str | None = None


class RecordClaimSummary(BaseModel):
    """One cataloguer's verdict about one pair, as a record reader sees it.

    Its own model rather than `authority_linking.LinkClaimSummary`, which
    says the same thing: that module imports this one, so reusing it would
    close a cycle. The reader here also needs less — who claimed it and the
    confidences it was weighed against belong on the claim screen, not on
    every row of a result list.
    """

    #: The target base, matching `LinkAttemptSummary.base`. Together with the
    #: two below this is the key a reader joins on to mark an attempt row.
    base: str
    authority_base: str
    authority_sysno: str
    #: SameWork or NotSameWork.
    verdict: str
    note: str | None = None
    claimed_at: datetime
    #: Whether the evidence has moved against this claim since it was made.
    #: The claim still decides the answer; this only asks for a look.
    needs_review: bool = False


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
    type_of_record: str | None = None
    bibliographic_level: str | None = None
    state: list[str] = []
    authority_links: list[AuthorityLinkSummary] = []
    #: Everything the linkers had to say, links and gaps alike, in rank order.
    #: What `authority_links` leaves out: the records with no link and the
    #: reason, and the alternatives an accepted link was chosen over.
    link_attempts: list[LinkAttemptSummary] = []
    #: What cataloguers have said about those attempts. Carried separately
    #: rather than folded into the rows because a claim can name a record no
    #: linker returned — ruling the machine's answer out in favour of one of
    #: those is the point — and such a claim has no row to sit on.
    claims: list[RecordClaimSummary] = []
    comparisons: list[ComparisonSummary] = []
    validations: list[ValidationSummary] = []
    latest_sync: datetime | None = None
    latest_transaction: datetime | None = None
    processed_at: datetime | None = None
    #: Why the last pass could not read this record, when it could not. The
    #: message is the only thing that turns a Broken state into something
    #: somebody can act on — it names the field MARC failed at.
    processing_error: str | None = None


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
    #: Which values of ``target_field`` to cross-tabulate, or every one of
    #: them when absent.
    #:
    #: A preview is what the dashboard would look like if this one value were
    #: filtered on, so it costs a pass over the analytics table per value. For
    #: a field with four values that is free and asking for all of them is
    #: right. ``link_agencies`` has 263 and most of them name fewer than ten
    #: records: previewing the whole field meant two queries per value — about
    #: eighty seconds of database time — to answer a hover over one pill, and
    #: all but a dozen of those values were not even on screen.
    #:
    #: The client sends the values it is showing. It is a bound on work, not a
    #: filter on the answer: the response is keyed by target value, so a path
    #: where narrowing saves nothing may return more than was asked for.
    target_values: list[str] | None = None


class FacetsPreviewEntry(BaseModel):
    """Facet distributions for all OTHER fields when target_field == target_value."""

    target_value: str
    facets: list[FacetResult]
    histograms: list[HistogramResult]
    total: int


class FacetsPreviewResponse(BaseModel):
    target_field: str
    previews: list[FacetsPreviewEntry]

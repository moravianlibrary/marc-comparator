from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.comparison import Comparison
from entities.record_review import RecordReview
from entities.validation import Validation

from .models import (
    AuthorityLinkSummary,
    ComparisonSummary,
    RecordFilter,
    RecordSummary,
    SearchRecordsRequest,
    SearchRecordsResponse,
    ValidationSummary,
)


SORT_COLUMNS = {
    "id": CatalogRecord.id,
    "base": CatalogRecord.base,
    "system_number": CatalogRecord.system_number,
    "latest_sync": CatalogRecord.latest_sync,
    "updated_at": CatalogRecord.updated_at,
}

# Maps filter attribute name -> (relationship attribute, column to filter on)
RELATIONSHIP_FILTERS = {
    "authority_link_linkers": (CatalogRecord.authority_links, AuthorityLink.linker),
    "authority_link_bases": (CatalogRecord.authority_links, AuthorityLink.base),
    "validators": (CatalogRecord.validations, Validation.validator),
}

BOOL_FILTERS = {
    "deleted": CatalogRecord.deleted,
}

MATCH_QUALITY_RANGES = {
    "Excellent": (0.9, None),
    "Moderate": (0.7, 0.9),
    "Poor": (None, 0.7),
}


def build_filtered_query(db: Session, filters: RecordFilter):
    """Build a filtered SQLAlchemy query for CatalogRecord. Used by task workers."""
    query = db.query(CatalogRecord)
    return _apply_filters(query, filters)


def search_records(request: SearchRecordsRequest, db: Session) -> SearchRecordsResponse:
    query = db.query(CatalogRecord).filter(
        CatalogRecord.source_type == CatalogRecordSource.Main
    )
    query = _apply_filters(query, request.filters)

    total = query.count()

    sort_col = SORT_COLUMNS.get(request.sort_by, CatalogRecord.id)
    if request.sort_order == "desc":
        sort_col = sort_col.desc()
    query = query.order_by(sort_col)

    offset = (request.page - 1) * request.page_size
    records = query.offset(offset).limit(request.page_size).all()

    return SearchRecordsResponse(
        items=[_to_summary(r) for r in records],
        total=total,
        page=request.page,
        page_size=request.page_size,
    )


def _apply_filters(query, filters: RecordFilter):
    if filters.record_ids:
        query = query.filter(CatalogRecord.id.in_(filters.record_ids))

    if filters.text_query:
        query = query.filter(
            CatalogRecord.search_vector.op("@@")(
                func.plainto_tsquery("simple", filters.text_query)
            )
        )

    if filters.bases:
        query = query.filter(CatalogRecord.base.in_(filters.bases))

    if filters.type_of_record:
        query = query.filter(CatalogRecord._type_of_record.in_(filters.type_of_record))

    if filters.bibliographic_level:
        query = query.filter(CatalogRecord._bibliographic_level.in_(filters.bibliographic_level))

    for attr, column in BOOL_FILTERS.items():
        if (value := getattr(filters, attr)) is not None:
            query = query.filter(column == value)

    if filters.processed is not None:
        query = query.filter(
            CatalogRecord.processed_at.isnot(None)
            if filters.processed
            else CatalogRecord.processed_at.is_(None)
        )

    if filters.review_statuses:
        has_current = CatalogRecord.reviews.any(RecordReview.status == "current")
        clauses = []
        for rs in filters.review_statuses:
            if rs == "Unreviewed":
                clauses.append(~has_current)
            else:
                # Both Reviewed and PartiallyReviewed require at least one current review
                clauses.append(has_current)
        query = query.filter(or_(*clauses))

    for attr, (relationship, column) in RELATIONSHIP_FILTERS.items():
        if values := getattr(filters, attr):
            query = query.filter(relationship.any(column.in_(values)))

    if filters.comparison_bases:
        query = query.filter(
            CatalogRecord.comparisons.any(
                Comparison.base.in_(filters.comparison_bases)
            )
        )

    # match_qualities: filter via JSONB overall_score
    if filters.match_qualities:
        score_col = Comparison._result["overall_score"].as_float()
        conditions = []
        for quality in filters.match_qualities:
            lo, hi = MATCH_QUALITY_RANGES.get(quality, (None, None))
            if lo is not None and hi is not None:
                conditions.append((score_col >= lo) & (score_col < hi))
            elif lo is not None:
                conditions.append(score_col >= lo)
            elif hi is not None:
                conditions.append(score_col < hi)
        if conditions:
            query = query.filter(CatalogRecord.comparisons.any(or_(*conditions)))

    # validation_statuses: JSONB filter
    if filters.validation_statuses:
        status_col = Validation._result["status"].as_string()
        query = query.filter(
            CatalogRecord.validations.any(status_col.in_(filters.validation_statuses))
        )

    # validation_target_tags: JSONB filter
    if filters.validation_target_tags:
        tag_col = Validation._result["target"]["tag"].as_string()
        query = query.filter(
            CatalogRecord.validations.any(tag_col.in_(filters.validation_target_tags))
        )

    # score_min / score_max: JSONB filter on comparison overall_score
    if filters.score_min is not None:
        score_col = Comparison._result["overall_score"].as_float()
        query = query.filter(
            CatalogRecord.comparisons.any(score_col >= filters.score_min)
        )
    if filters.score_max is not None:
        score_col = Comparison._result["overall_score"].as_float()
        query = query.filter(
            CatalogRecord.comparisons.any(score_col <= filters.score_max)
        )

    # NOTE: field_explanations filter is not implemented here because it would
    # require iterating over a JSONB array (field_results[*].explanation), which
    # cannot be expressed as a simple JSONB path query in SQLAlchemy/PostgreSQL.

    return query


def _to_summary(record: CatalogRecord) -> RecordSummary:
    return RecordSummary(
        id=record.id,
        base=record.base,
        system_number=record.system_number,
        title=record.title,
        authors=record.authors or [],
        type_of_record=record.type_of_record,
        bibliographic_level=record.bibliographic_level,
        state=[s.value for s in record.state],
        authority_links=[
            AuthorityLinkSummary(
                linker=al.linker,
                base=al.base,
                authority_record_id=al.authority_record_id,
            )
            for al in record.authority_links
        ],
        comparisons=[
            ComparisonSummary(
                comparator=c.comparator,
                base=c.base,
                other_record_id=c.other_record_id,
                overall_score=c.overall_score,
                match_quality=c.match_quality,
            )
            for c in record.comparisons
        ],
        validations=[
            ValidationSummary(
                validator=v.validator,
                target_tag=v.target.tag,
                status=v.status,
            )
            for v in record.validations
        ],
        latest_sync=record.latest_sync,
        latest_transaction=record.latest_transaction,
        processed_at=record.processed_at,
    )

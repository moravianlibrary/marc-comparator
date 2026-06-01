from sqlalchemy import func
from sqlalchemy.orm import Session

from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.comparison import Comparison

from .filter_orm import apply_conditions
from .filter_spec import parse_filters
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


def build_filtered_query(db: Session, filters: RecordFilter):
    """Build a filtered SQLAlchemy query for CatalogRecord. Used by task workers."""
    query = db.query(CatalogRecord).filter(
        CatalogRecord.source_type == CatalogRecordSource.Main
    )
    return apply_conditions(query, parse_filters(filters))


def search_records(request: SearchRecordsRequest, db: Session) -> SearchRecordsResponse:
    query = db.query(CatalogRecord).filter(
        CatalogRecord.source_type == CatalogRecordSource.Main
    )
    query = apply_conditions(query, parse_filters(request.filters))

    total = query.count()

    if request.sort_by == "comparison_score":
        avg_score = (
            func.coalesce(
                func.avg(Comparison._result["overall_score"].as_float()), 0
            )
        ).label("avg_score")
        query = (
            query
            .outerjoin(Comparison, Comparison.main_record_id == CatalogRecord.id)
            .group_by(CatalogRecord.id)
            .order_by(
                avg_score.desc() if request.sort_order == "desc" else avg_score.asc()
            )
        )
    else:
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

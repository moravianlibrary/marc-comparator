from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import (
    FacetBucket,
    FacetResult,
    FacetsRequest,
    FacetsResponse,
    FacetsPreviewEntry,
    FacetsPreviewRequest,
    FacetsPreviewResponse,
    HistogramBucket,
    HistogramResult,
    RecordFilter,
)

VIEW = "catalog_records_analytics"

SCALAR_FACETS = ["base", "type_of_record", "bibliographic_level", "review_status"]
BOOL_FACETS = {
    "is_deleted": ("Active", "Deleted"),
    "is_processed": ("Unprocessed", "Processed"),
}
ARRAY_FACETS = [
    "authority_link_linkers",
    "authority_link_bases",
    "comparison_bases",
    "match_qualities",
    "validators",
    "validation_statuses",
    "validation_target_tags",
    "validation_reasons",
    "field_explanations",
]

# Maps RecordFilter field names -> matview column names (where they differ)
_FILTER_TO_MATVIEW = {
    "bases": "base",
    "deleted": "is_deleted",
    "processed": "is_processed",
    "review_statuses": "review_status",
}


def get_facets(request: FacetsRequest, db: Session) -> FacetsResponse:
    db.execute(text("SET LOCAL duckdb.force_execution = true"))

    where, params = _build_where(request.filters)
    facets = []

    for field in SCALAR_FACETS:
        rows = db.execute(text(
            f"SELECT {field} AS val, count(*) AS cnt "
            f"FROM {VIEW} {where} AND {field} IS NOT NULL "
            f"GROUP BY val ORDER BY cnt DESC"
        ), params).mappings().all()
        facets.append(FacetResult(
            field=field,
            buckets=[FacetBucket(key=r["val"], count=r["cnt"]) for r in rows],
        ))

    for field, (false_label, true_label) in BOOL_FACETS.items():
        rows = db.execute(text(
            f"SELECT {field} AS val, count(*) AS cnt "
            f"FROM {VIEW} {where} GROUP BY val"
        ), params).mappings().all()
        facets.append(FacetResult(
            field=field,
            buckets=[
                FacetBucket(
                    key=true_label if r["val"] else false_label,
                    count=r["cnt"],
                )
                for r in rows
            ],
        ))

    for field in ARRAY_FACETS:
        rows = db.execute(text(
            f"SELECT val, count(*) AS cnt "
            f"FROM {VIEW}, unnest({field}) AS t(val) "
            f"{where} GROUP BY val ORDER BY cnt DESC"
        ), params).mappings().all()
        facets.append(FacetResult(
            field=field,
            buckets=[FacetBucket(key=r["val"], count=r["cnt"]) for r in rows],
        ))

    # Score histogram
    hist_rows = db.execute(text(
        f"SELECT floor(val / 0.05) * 0.05 AS bucket_min, "
        f"       floor(val / 0.05) * 0.05 + 0.05 AS bucket_max, "
        f"       count(*) AS cnt "
        f"FROM {VIEW}, unnest(overall_scores) AS t(val) "
        f"{where} GROUP BY bucket_min, bucket_max ORDER BY bucket_min"
    ), params).mappings().all()

    histograms = []
    if hist_rows:
        histograms.append(HistogramResult(
            field="overall_score",
            buckets=[
                HistogramBucket(
                    min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"]
                )
                for r in hist_rows
            ],
        ))

    total_rows = db.execute(text(
        f"SELECT count(*) AS cnt FROM {VIEW} {where}"
    ), params).mappings().all()
    total = total_rows[0]["cnt"] if total_rows else 0

    return FacetsResponse(facets=facets, histograms=histograms, total=total)


def get_facets_preview(
    request: FacetsPreviewRequest, db: Session
) -> FacetsPreviewResponse:
    """For each value of target_field, compute facet distributions of all OTHER fields.

    Used for hover preview: client prefetches on cursor proximity to a chart,
    then picks the right slice from the cached response on hover — no new request needed.
    """
    db.execute(text("SET LOCAL duckdb.force_execution = true"))

    where, params = _build_where(request.filters)
    target = request.target_field

    if target in SCALAR_FACETS:
        val_rows = db.execute(text(
            f"SELECT DISTINCT {target} AS val FROM {VIEW} {where}"
        ), params).mappings().all()
    elif target in ARRAY_FACETS:
        val_rows = db.execute(text(
            f"SELECT DISTINCT val FROM {VIEW}, unnest({target}) AS t(val) {where}"
        ), params).mappings().all()
    elif target in BOOL_FACETS:
        val_rows = db.execute(text(
            f"SELECT DISTINCT {target} AS val FROM {VIEW} {where}"
        ), params).mappings().all()
    else:
        return FacetsPreviewResponse(target_field=target, previews=[])

    previews = []
    for row in val_rows:
        target_value = row["val"]
        preview_filter = request.filters.model_copy()
        _add_target_filter(preview_filter, target, target_value)
        preview_resp = get_facets(FacetsRequest(filters=preview_filter), db)

        if target in BOOL_FACETS:
            false_label, true_label = BOOL_FACETS[target]
            label = true_label if target_value else false_label
        else:
            label = str(target_value)

        previews.append(FacetsPreviewEntry(
            target_value=label,
            facets=preview_resp.facets,
            histograms=preview_resp.histograms,
            total=preview_resp.total,
        ))

    return FacetsPreviewResponse(target_field=target, previews=previews)


def _add_target_filter(filters: RecordFilter, field: str, value) -> None:
    """Mutate filters to add a single target value constraint."""
    if field in ("base", "type_of_record", "bibliographic_level", "review_status"):
        attr = {"base": "bases", "review_status": "review_statuses"}.get(field, field)
        current = getattr(filters, attr) or []
        setattr(filters, attr, [*current, str(value)])
    elif field in BOOL_FACETS:
        attr = {
            "is_deleted": "deleted",
            "is_processed": "processed",
        }[field]
        setattr(filters, attr, bool(value))
    elif field in ARRAY_FACETS:
        current = getattr(filters, field) or []
        setattr(filters, field, [*current, str(value)])


def _build_where(filters: RecordFilter) -> tuple[str, dict]:
    conditions = ["TRUE"]
    params = {}

    if filters.bases:
        conditions.append("base = ANY(:bases)")
        params["bases"] = filters.bases
    if filters.deleted is not None:
        conditions.append("is_deleted = :is_deleted")
        params["is_deleted"] = filters.deleted
    if filters.review_statuses:
        conditions.append("review_status = ANY(:review_statuses)")
        params["review_statuses"] = filters.review_statuses
    if filters.processed is not None:
        conditions.append("is_processed = :is_processed")
        params["is_processed"] = filters.processed
    if filters.type_of_record:
        conditions.append("type_of_record = ANY(:type_of_record)")
        params["type_of_record"] = filters.type_of_record
    if filters.bibliographic_level:
        conditions.append("bibliographic_level = ANY(:bib_level)")
        params["bib_level"] = filters.bibliographic_level

    # Array overlap: PG's && operator
    for field in ARRAY_FACETS:
        if values := getattr(filters, field, None):
            conditions.append(f"CAST({field} AS text[]) && :arr_{field}")
            params[f"arr_{field}"] = values

    if filters.score_min is not None:
        conditions.append(
            "EXISTS (SELECT 1 FROM unnest(overall_scores) s WHERE s >= :score_min)"
        )
        params["score_min"] = filters.score_min
    if filters.score_max is not None:
        conditions.append(
            "EXISTS (SELECT 1 FROM unnest(overall_scores) s WHERE s <= :score_max)"
        )
        params["score_max"] = filters.score_max

    where = "WHERE " + " AND ".join(conditions)
    return where, params

from adapters.clickhouse import query

from .models import (
    FacetBucket,
    FacetFilter,
    FacetResult,
    FacetsRequest,
    FacetsResponse,
    FacetsPreviewEntry,
    FacetsPreviewRequest,
    FacetsPreviewResponse,
    HistogramBucket,
    HistogramResult,
)

TABLE = "catalog_records_analytics"

# Simple scalar facets
SCALAR_FACETS = ["base", "type_of_record", "bibliographic_level"]

# Array facets (need ARRAY JOIN)
ARRAY_FACETS = {
    "comparators": "comparators",
    "comparison_bases": "comparison_bases",
    "match_qualities": "match_qualities",
    "validators": "validators",
    "validation_statuses": "validation_statuses",
    "authority_link_bases": "authority_link_bases",
    "authority_link_linkers": "authority_link_linkers",
    "field_explanations": "field_explanations",
    "validation_target_tags": "validation_target_tags",
}

# Boolean facets (reported as "Active"/"Deleted", "Visible"/"Hidden", etc.)
BOOL_FACETS = {
    "is_deleted": ("Active", "Deleted"),
    "is_hidden": ("Visible", "Hidden"),
    "is_processed": ("Processed", "Unprocessed"),
}


def get_facets(request: FacetsRequest) -> FacetsResponse:
    where_clause, params = _build_where(request.filters)

    facets = []

    # Scalar facets
    for field in SCALAR_FACETS:
        rows = query(
            f"SELECT {field} AS val, count() AS cnt "
            f"FROM {TABLE} {where_clause} "
            f"GROUP BY val ORDER BY cnt DESC",
            params,
        )
        facets.append(FacetResult(
            field=field,
            buckets=[FacetBucket(key=r["val"], count=r["cnt"]) for r in rows],
        ))

    # Boolean facets
    for field, (true_label, false_label) in BOOL_FACETS.items():
        rows = query(
            f"SELECT {field} AS val, count() AS cnt "
            f"FROM {TABLE} {where_clause} "
            f"GROUP BY val ORDER BY val",
            params,
        )
        facets.append(FacetResult(
            field=field,
            buckets=[
                FacetBucket(
                    key=true_label if r["val"] == 0 else false_label,
                    count=r["cnt"],
                )
                for r in rows
            ],
        ))

    # Array facets
    for facet_name, col_name in ARRAY_FACETS.items():
        rows = query(
            f"SELECT val, count() AS cnt "
            f"FROM {TABLE} "
            f"ARRAY JOIN {col_name} AS val "
            f"{where_clause} "
            f"GROUP BY val ORDER BY cnt DESC",
            params,
        )
        facets.append(FacetResult(
            field=facet_name,
            buckets=[FacetBucket(key=r["val"], count=r["cnt"]) for r in rows],
        ))

    # Histogram for overall scores
    histograms = []
    hist_rows = query(
        f"SELECT "
        f"  floor(val / 0.05) * 0.05 AS bucket_min, "
        f"  floor(val / 0.05) * 0.05 + 0.05 AS bucket_max, "
        f"  count() AS cnt "
        f"FROM {TABLE} "
        f"ARRAY JOIN overall_scores AS val "
        f"{where_clause} "
        f"GROUP BY bucket_min, bucket_max ORDER BY bucket_min",
        params,
    )
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

    total_rows = query(f"SELECT count() AS cnt FROM {TABLE} {where_clause}", params)
    total = total_rows[0]["cnt"] if total_rows else 0

    return FacetsResponse(facets=facets, histograms=histograms, total=total)


def get_facets_preview(request: FacetsPreviewRequest) -> FacetsPreviewResponse:
    """For each value of target_field, compute facet distributions of all OTHER fields.

    Used for hover preview: client prefetches on cursor proximity to a chart,
    then picks the right slice from the cached response on hover.
    """
    where_clause, params = _build_where(request.filters)

    # Get distinct values of the target field
    target = request.target_field
    if target in SCALAR_FACETS:
        val_rows = query(
            f"SELECT DISTINCT {target} AS val FROM {TABLE} {where_clause}",
            params,
        )
    elif target in ARRAY_FACETS:
        col = ARRAY_FACETS[target]
        val_rows = query(
            f"SELECT DISTINCT val FROM {TABLE} ARRAY JOIN {col} AS val {where_clause}",
            params,
        )
    elif target in BOOL_FACETS:
        val_rows = query(
            f"SELECT DISTINCT {target} AS val FROM {TABLE} {where_clause}",
            params,
        )
    else:
        return FacetsPreviewResponse(target_field=target, previews=[])

    previews = []
    for row in val_rows:
        target_value = row["val"]

        # Build a FacetFilter with the target value added
        preview_filter = request.filters.model_copy()
        _add_target_filter(preview_filter, target, target_value)

        # Reuse get_facets to compute all facets with this extra filter
        preview_resp = get_facets(FacetsRequest(filters=preview_filter))

        # Label for booleans
        if target in BOOL_FACETS:
            true_label, false_label = BOOL_FACETS[target]
            label = true_label if target_value == 0 else false_label
        else:
            label = str(target_value)

        previews.append(FacetsPreviewEntry(
            target_value=label,
            facets=preview_resp.facets,
            histograms=preview_resp.histograms,
            total=preview_resp.total,
        ))

    return FacetsPreviewResponse(target_field=target, previews=previews)


def _add_target_filter(filters: FacetFilter, field: str, value) -> None:
    """Mutate filters to add a single target value constraint."""
    if field in ("base", "type_of_record", "bibliographic_level"):
        current = getattr(filters, field) or []
        setattr(filters, field, [*current, str(value)])
    elif field in BOOL_FACETS:
        setattr(filters, field, bool(value))
    elif field in ARRAY_FACETS:
        current = getattr(filters, field) or []
        setattr(filters, field, [*current, str(value)])


def _build_where(filters: FacetFilter) -> tuple[str, dict]:
    conditions = []
    params = {}

    if filters.base:
        conditions.append("base IN {base:Array(String)}")
        params["base"] = filters.base
    if filters.is_deleted is not None:
        conditions.append(f"is_deleted = {int(filters.is_deleted)}")
    if filters.is_hidden is not None:
        conditions.append(f"is_hidden = {int(filters.is_hidden)}")
    if filters.is_processed is not None:
        conditions.append(f"is_processed = {int(filters.is_processed)}")
    if filters.type_of_record:
        conditions.append("type_of_record IN {type_of_record:Array(String)}")
        params["type_of_record"] = filters.type_of_record
    if filters.bibliographic_level:
        conditions.append("bibliographic_level IN {bib_level:Array(String)}")
        params["bib_level"] = filters.bibliographic_level
    if filters.comparators:
        conditions.append("hasAny(comparators, {comparators:Array(String)})")
        params["comparators"] = filters.comparators
    if filters.comparison_bases:
        conditions.append("hasAny(comparison_bases, {comp_bases:Array(String)})")
        params["comp_bases"] = filters.comparison_bases
    if filters.match_qualities:
        conditions.append("hasAny(match_qualities, {match_qualities:Array(String)})")
        params["match_qualities"] = filters.match_qualities
    if filters.validators:
        conditions.append("hasAny(validators, {validators:Array(String)})")
        params["validators"] = filters.validators
    if filters.validation_statuses:
        conditions.append("hasAny(validation_statuses, {validation_statuses:Array(String)})")
        params["validation_statuses"] = filters.validation_statuses
    if filters.authority_link_bases:
        conditions.append("hasAny(authority_link_bases, {al_bases:Array(String)})")
        params["al_bases"] = filters.authority_link_bases
    if filters.authority_link_linkers:
        conditions.append("hasAny(authority_link_linkers, {al_linkers:Array(String)})")
        params["al_linkers"] = filters.authority_link_linkers
    if filters.field_explanations:
        conditions.append("hasAny(field_explanations, {field_expl:Array(String)})")
        params["field_expl"] = filters.field_explanations
    if filters.validation_target_tags:
        conditions.append("hasAny(validation_target_tags, {val_tags:Array(String)})")
        params["val_tags"] = filters.validation_target_tags
    if filters.score_min is not None:
        conditions.append("arrayExists(x -> x >= {score_min:Float64}, overall_scores)")
        params["score_min"] = filters.score_min
    if filters.score_max is not None:
        conditions.append("arrayExists(x -> x <= {score_max:Float64}, overall_scores)")
        params["score_max"] = filters.score_max

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where, params

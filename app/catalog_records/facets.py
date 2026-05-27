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

TABLE = "catalog_records_analytics"

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

_FILTER_TO_MATVIEW = {
    "bases": "base",
    "deleted": "is_deleted",
    "processed": "is_processed",
    "review_statuses": "review_status",
}

# ---- GROUPING SETS column list for scalar + bool facets ----
_GS_COLUMNS = SCALAR_FACETS + list(BOOL_FACETS.keys())


def get_facets(request: FacetsRequest, db: Session) -> FacetsResponse:
    where, params = _build_where(request.filters)

    # --- 1. Scalar + bool facets via GROUPING SETS (single scan) ---
    gs_sets = ", ".join(f"({col})" for col in _GS_COLUMNS)
    col_list = ", ".join(_GS_COLUMNS)
    rows = db.execute(text(
        f"SELECT {col_list}, count(*) AS cnt "
        f"FROM {TABLE} {where} "
        f"GROUP BY GROUPING SETS ({gs_sets})"
    ), params).mappings().all()

    facets = _parse_grouping_sets_rows(rows)

    # --- 2. Array facets (one query per array, needs unnest) ---
    for field in ARRAY_FACETS:
        arr_rows = db.execute(text(
            f"SELECT val, count(*) AS cnt "
            f"FROM {TABLE}, unnest({field}) AS t(val) "
            f"{where} GROUP BY val ORDER BY cnt DESC"
        ), params).mappings().all()
        facets.append(FacetResult(
            field=field,
            buckets=[FacetBucket(key=r["val"], count=r["cnt"]) for r in arr_rows],
        ))

    # --- 3. Score histogram ---
    histograms = []
    hist_rows = db.execute(text(
        f"SELECT floor(val / 0.05) * 0.05 AS bucket_min, "
        f"       floor(val / 0.05) * 0.05 + 0.05 AS bucket_max, "
        f"       count(*) AS cnt "
        f"FROM {TABLE}, unnest(overall_scores) AS t(val) "
        f"{where} GROUP BY bucket_min, bucket_max ORDER BY bucket_min"
    ), params).mappings().all()
    if hist_rows:
        histograms.append(HistogramResult(
            field="overall_score",
            buckets=[
                HistogramBucket(min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"])
                for r in hist_rows
            ],
        ))

    # --- 4. Total count ---
    total_row = db.execute(text(
        f"SELECT count(*) AS cnt FROM {TABLE} {where}"
    ), params).mappings().first()
    total = total_row["cnt"] if total_row else 0

    return FacetsResponse(facets=facets, histograms=histograms, total=total)


def get_facets_preview(
    request: FacetsPreviewRequest, db: Session
) -> FacetsPreviewResponse:
    """Compute facet distributions for every value of target_field in a single pass.

    For scalar/bool targets: one GROUPING SETS query grouped by (target, facet_dims).
    For array targets: unnest first, then group.
    """
    where, params = _build_where(request.filters)
    target = request.target_field

    # --- Build the preview query: all facets grouped by target_value ---
    if target in SCALAR_FACETS or target in BOOL_FACETS:
        target_col = target
    elif target in ARRAY_FACETS:
        target_col = "target_val"
    else:
        return FacetsPreviewResponse(target_field=target, previews=[])

    # Scalar + bool facets grouped by target
    other_gs_cols = [c for c in _GS_COLUMNS if c != target]
    gs_sets = ", ".join(f"({col})" for col in other_gs_cols)

    if target in ARRAY_FACETS:
        from_clause = f"{TABLE}, unnest({target}) AS t(target_val)"
    else:
        from_clause = TABLE

    col_list = ", ".join(other_gs_cols)
    scalar_rows = db.execute(text(
        f"SELECT {target_col} AS target_value, {col_list}, count(*) AS cnt "
        f"FROM {from_clause} {where} "
        f"GROUP BY {target_col}, GROUPING SETS ({gs_sets})"
    ), params).mappings().all()

    # Array facets grouped by target (one query per array facet)
    array_results: dict[str, list] = {}
    for field in ARRAY_FACETS:
        if field == target:
            continue
        if target in ARRAY_FACETS:
            arr_from = f"{TABLE}, unnest({target}) AS t(target_val), unnest({field}) AS t2(val)"
        else:
            arr_from = f"{TABLE}, unnest({field}) AS t2(val)"
        arr_rows = db.execute(text(
            f"SELECT {target_col} AS target_value, t2.val, count(*) AS cnt "
            f"FROM {arr_from} {where} "
            f"GROUP BY {target_col}, t2.val ORDER BY cnt DESC"
        ), params).mappings().all()
        for r in arr_rows:
            tv = str(r["target_value"])
            array_results.setdefault(tv, {}).setdefault(field, []).append(
                FacetBucket(key=r["val"], count=r["cnt"])
            )

    # Histogram grouped by target
    if target in ARRAY_FACETS:
        hist_from = f"{TABLE}, unnest({target}) AS t(target_val), unnest(overall_scores) AS t3(val)"
    else:
        hist_from = f"{TABLE}, unnest(overall_scores) AS t3(val)"
    hist_rows = db.execute(text(
        f"SELECT {target_col} AS target_value, "
        f"       floor(t3.val / 0.05) * 0.05 AS bucket_min, "
        f"       floor(t3.val / 0.05) * 0.05 + 0.05 AS bucket_max, "
        f"       count(*) AS cnt "
        f"FROM {hist_from} {where} "
        f"GROUP BY {target_col}, bucket_min, bucket_max ORDER BY bucket_min"
    ), params).mappings().all()
    hist_by_target: dict[str, list[HistogramBucket]] = {}
    for r in hist_rows:
        tv = str(r["target_value"])
        hist_by_target.setdefault(tv, []).append(
            HistogramBucket(min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"])
        )

    # Total per target
    if target in ARRAY_FACETS:
        total_from = f"{TABLE}, unnest({target}) AS t(target_val)"
    else:
        total_from = TABLE
    total_rows = db.execute(text(
        f"SELECT {target_col} AS target_value, count(*) AS cnt "
        f"FROM {total_from} {where} "
        f"GROUP BY {target_col}"
    ), params).mappings().all()
    total_by_target = {str(r["target_value"]): r["cnt"] for r in total_rows}

    # --- Assemble previews ---
    # Collect all target values from scalar_rows
    target_values = set()
    for r in scalar_rows:
        target_values.add(str(r["target_value"]))
    for tv in total_by_target:
        target_values.add(tv)

    previews = []
    for tv in sorted(target_values):
        # Parse scalar/bool facets for this target value
        tv_facets = _parse_preview_grouping_rows(scalar_rows, tv, other_gs_cols)

        # Add array facets
        tv_arrays = array_results.get(tv, {})
        for field in ARRAY_FACETS:
            if field == target:
                continue
            buckets = tv_arrays.get(field, [])
            tv_facets.append(FacetResult(field=field, buckets=buckets))

        # Histogram
        tv_histograms = []
        if tv in hist_by_target:
            tv_histograms.append(HistogramResult(
                field="overall_score", buckets=hist_by_target[tv]
            ))

        # Label for bool targets
        if target in BOOL_FACETS:
            false_label, true_label = BOOL_FACETS[target]
            label = true_label if tv == "True" else false_label
        else:
            label = tv

        previews.append(FacetsPreviewEntry(
            target_value=label,
            facets=tv_facets,
            histograms=tv_histograms,
            total=total_by_target.get(tv, 0),
        ))

    return FacetsPreviewResponse(target_field=target, previews=previews)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_grouping_sets_rows(rows: list) -> list[FacetResult]:
    """Parse GROUPING SETS result rows into FacetResult list.

    Each row has exactly one non-NULL dimension column (the one being grouped).
    """
    buckets_by_field: dict[str, list[FacetBucket]] = {}

    for row in rows:
        for col in _GS_COLUMNS:
            if row[col] is not None:
                if col in BOOL_FACETS:
                    false_label, true_label = BOOL_FACETS[col]
                    label = true_label if row[col] else false_label
                else:
                    label = str(row[col])
                buckets_by_field.setdefault(col, []).append(
                    FacetBucket(key=label, count=row["cnt"])
                )
                break  # only one column is non-NULL per GROUPING SETS row

    result = []
    for field in SCALAR_FACETS:
        result.append(FacetResult(
            field=field,
            buckets=sorted(buckets_by_field.get(field, []), key=lambda b: -b.count),
        ))
    for field in BOOL_FACETS:
        result.append(FacetResult(
            field=field,
            buckets=buckets_by_field.get(field, []),
        ))
    return result


def _parse_preview_grouping_rows(
    rows: list, target_value: str, gs_columns: list[str]
) -> list[FacetResult]:
    """Extract facets for a specific target_value from GROUPING SETS preview rows."""
    buckets_by_field: dict[str, list[FacetBucket]] = {}

    for row in rows:
        if str(row["target_value"]) != target_value:
            continue
        for col in gs_columns:
            if row[col] is not None:
                if col in BOOL_FACETS:
                    false_label, true_label = BOOL_FACETS[col]
                    label = true_label if row[col] else false_label
                else:
                    label = str(row[col])
                buckets_by_field.setdefault(col, []).append(
                    FacetBucket(key=label, count=row["cnt"])
                )
                break

    result = []
    for field in SCALAR_FACETS:
        if field in [c for c in gs_columns]:
            result.append(FacetResult(
                field=field,
                buckets=sorted(buckets_by_field.get(field, []), key=lambda b: -b.count),
            ))
    for field in BOOL_FACETS:
        if field in gs_columns:
            result.append(FacetResult(
                field=field,
                buckets=buckets_by_field.get(field, []),
            ))
    return result


def _build_where(filters: RecordFilter) -> tuple[str, dict]:
    conditions = ["TRUE"]
    params: dict = {}

    if filters.record_ids:
        conditions.append("id = ANY(:record_ids)")
        params["record_ids"] = filters.record_ids
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

from sqlalchemy import text
from sqlalchemy.orm import Session

from .filter_spec import parse_filters
from .filter_sql import compile_conditions
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

# ---- GROUPING SETS column list for scalar + bool facets ----
_GS_COLUMNS = SCALAR_FACETS + list(BOOL_FACETS.keys())


def get_facets(request: FacetsRequest, db: Session) -> FacetsResponse:
    where, params = compile_conditions(parse_filters(request.filters))

    # --- 1. Scalar + bool facets + total via GROUPING SETS (single scan) ---
    gs_sets = ", ".join(f"({col})" for col in _GS_COLUMNS)
    col_list = ", ".join(_GS_COLUMNS)
    rows = db.execute(text(
        f"SELECT {col_list}, count(*) AS cnt "
        f"FROM {TABLE} {where} "
        f"GROUP BY GROUPING SETS ({gs_sets}, ())"
    ), params).mappings().all()

    facets = _parse_grouping_sets_rows(rows)

    # --- 2. Array facets (single UNION ALL query) ---
    parts = []
    for field in ARRAY_FACETS:
        parts.append(
            f"SELECT '{field}' AS facet_field, val, count(*) AS cnt "
            f"FROM {TABLE}, unnest({field}) AS t(val) "
            f"{where} GROUP BY val"
        )
    arr_rows = db.execute(
        text(" UNION ALL ".join(parts)), params
    ).mappings().all()
    arr_by_field: dict[str, list[FacetBucket]] = {}
    for r in arr_rows:
        arr_by_field.setdefault(r["facet_field"], []).append(
            FacetBucket(key=r["val"], count=r["cnt"])
        )
    for field in ARRAY_FACETS:
        buckets = arr_by_field.get(field, [])
        buckets.sort(key=lambda b: -b.count)
        facets.append(FacetResult(field=field, buckets=buckets))

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

    # --- 4. Total count (from the empty () grouping set in query 1) ---
    total = 0
    for row in rows:
        if all(row[col] is None for col in _GS_COLUMNS):
            total = row["cnt"]
            break

    return FacetsResponse(facets=facets, histograms=histograms, total=total)


def get_facets_preview(
    request: FacetsPreviewRequest, db: Session
) -> FacetsPreviewResponse:
    """Compute facet distributions for every value of target_field.

    Uses 3 queries total:
      1. GROUPING SETS for scalar/bool facets + totals (includes empty set for counts)
      2. Single UNION ALL for all array facets
      3. Histogram
    """
    where, params = compile_conditions(parse_filters(request.filters))
    target = request.target_field

    if target in SCALAR_FACETS or target in BOOL_FACETS:
        target_col = target
    elif target in ARRAY_FACETS:
        target_col = "target_val"
    else:
        return FacetsPreviewResponse(target_field=target, previews=[])

    if target in ARRAY_FACETS:
        from_clause = f"{TABLE}, unnest({target}) AS t(target_val)"
    else:
        from_clause = TABLE

    # --- Query 1: Scalar/bool facets + totals via GROUPING SETS ---
    # The empty () set gives us count per target_value (total).
    other_gs_cols = [c for c in _GS_COLUMNS if c != target]
    gs_sets = ", ".join(f"({col})" for col in other_gs_cols)
    col_list = ", ".join(other_gs_cols)
    scalar_rows = db.execute(text(
        f"SELECT {target_col} AS target_value, {col_list}, count(*) AS cnt "
        f"FROM {from_clause} {where} "
        f"GROUP BY {target_col}, GROUPING SETS ({gs_sets}, ())"
    ), params).mappings().all()

    # --- Query 2: All array facets in a single UNION ALL ---
    array_fields = [f for f in ARRAY_FACETS if f != target]
    array_results: dict[str, dict[str, list[FacetBucket]]] = {}
    if array_fields:
        parts = []
        for field in array_fields:
            if target in ARRAY_FACETS:
                arr_from = f"{TABLE}, unnest({target}) AS t(target_val), unnest({field}) AS t2(val)"
            else:
                arr_from = f"{TABLE}, unnest({field}) AS t2(val)"
            parts.append(
                f"SELECT {target_col} AS target_value, "
                f"'{field}' AS facet_field, t2.val, count(*) AS cnt "
                f"FROM {arr_from} {where} "
                f"GROUP BY {target_col}, t2.val"
            )
        arr_rows = db.execute(
            text(" UNION ALL ".join(parts)), params
        ).mappings().all()
        for r in arr_rows:
            tv = str(r["target_value"])
            array_results.setdefault(tv, {}).setdefault(r["facet_field"], []).append(
                FacetBucket(key=r["val"], count=r["cnt"])
            )

    # --- Query 3: Histogram grouped by target ---
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

    # --- Assemble previews ---
    total_by_target, target_values = _extract_totals_and_targets(
        scalar_rows, other_gs_cols
    )

    previews = []
    for tv in sorted(target_values):
        tv_facets = _parse_preview_grouping_rows(scalar_rows, tv, other_gs_cols)

        tv_arrays = array_results.get(tv, {})
        for field in array_fields:
            buckets = tv_arrays.get(field, [])
            buckets.sort(key=lambda b: -b.count)
            tv_facets.append(FacetResult(field=field, buckets=buckets))

        tv_histograms = []
        if tv in hist_by_target:
            tv_histograms.append(HistogramResult(
                field="overall_score", buckets=hist_by_target[tv]
            ))

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

def _extract_totals_and_targets(
    rows: list, gs_columns: list[str]
) -> tuple[dict[str, int], set[str]]:
    """Extract per-target totals (from the empty grouping set) and all target values."""
    total_by_target: dict[str, int] = {}
    target_values: set[str] = set()

    for row in rows:
        tv = str(row["target_value"])
        target_values.add(tv)
        # The empty () grouping set produces rows where all facet columns are NULL
        if all(row[col] is None for col in gs_columns):
            total_by_target[tv] = row["cnt"]

    return total_by_target, target_values


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
        if field in gs_columns:
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

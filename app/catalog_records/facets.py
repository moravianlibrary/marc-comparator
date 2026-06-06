from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text
from sqlalchemy.orm import Session

from .analytics import CUBE_HIST_TABLE, CUBE_TABLE
from .filter_spec import parse_filters
from .filter_sql import compile_conditions
from .models import (
    FacetBucket,
    FacetResult,
    FacetsPreviewEntry,
    FacetsPreviewRequest,
    FacetsPreviewResponse,
    FacetsRequest,
    FacetsResponse,
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
_ALL_FACET_FIELDS = SCALAR_FACETS + list(BOOL_FACETS.keys()) + ARRAY_FACETS


def get_facets(request: FacetsRequest, db: Session) -> FacetsResponse:
    conditions = parse_filters(request.filters)

    # Unfiltered facets are exactly the cube's per-target totals — serve them
    # from the precomputed cube (the same source get_facets_preview already
    # uses) instead of rescanning 1.7M analytics rows (~5s of DB time).
    if not conditions:
        cube_response = _facets_from_cube(db)
        if cube_response is not None:
            return cube_response

    where, params = compile_conditions(conditions)
    return _facets_live(where, params, db)


def _facets_from_cube(db: Session) -> FacetsResponse | None:
    """Build the unfiltered facets response from the precomputed cube.

    Returns None when the cube has not been built yet (fresh install before
    the first rebuild_all) so the caller can fall back to live queries.
    """
    rows = (
        db.execute(
            text(
                f"SELECT target_field, target_value, cnt "
                f"FROM {CUBE_TABLE} WHERE facet_field = '_total_'"
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None

    buckets_by_field: dict[str, list[FacetBucket]] = {}
    for r in rows:
        buckets_by_field.setdefault(r["target_field"], []).append(
            FacetBucket(key=r["target_value"], count=r["cnt"])
        )

    facets = []
    for field in SCALAR_FACETS:
        facets.append(
            FacetResult(
                field=field,
                buckets=sorted(buckets_by_field.get(field, []), key=lambda b: -b.count),
            )
        )
    for field in BOOL_FACETS:
        facets.append(FacetResult(field=field, buckets=buckets_by_field.get(field, [])))
    for field in ARRAY_FACETS:
        facets.append(
            FacetResult(
                field=field,
                buckets=sorted(buckets_by_field.get(field, []), key=lambda b: -b.count),
            )
        )

    # is_deleted is NOT NULL, so its buckets partition all records exactly once.
    total = sum(b.count for b in buckets_by_field.get("is_deleted", []))

    hist_rows = (
        db.execute(
            text(
                f"SELECT bucket_min, bucket_max, sum(cnt)::bigint AS cnt "
                f"FROM {CUBE_HIST_TABLE} WHERE target_field = 'is_deleted' "
                f"GROUP BY bucket_min, bucket_max ORDER BY bucket_min"
            )
        )
        .mappings()
        .all()
    )
    histograms = []
    if hist_rows:
        histograms.append(
            HistogramResult(
                field="overall_score",
                buckets=[
                    HistogramBucket(min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"])
                    for r in hist_rows
                ],
            )
        )

    return FacetsResponse(facets=facets, histograms=histograms, total=total)


def _facets_live(where: str, params: dict, db: Session) -> FacetsResponse:
    """Compute facets with live queries, running the independent scans
    concurrently (same pattern as _preview_live_grouped) — wall time is the
    slowest scan instead of the sum of all eleven."""
    gs_sets = ", ".join(f"({col})" for col in _GS_COLUMNS)
    col_list = ", ".join(_GS_COLUMNS)
    gs_sql = (
        f"SELECT {col_list}, count(*) AS cnt "
        f"FROM {TABLE} {where} "
        f"GROUP BY GROUPING SETS ({gs_sets}, ())"
    )

    arr_sqls = {
        field: (
            f"SELECT val, count(*) AS cnt "
            f"FROM {TABLE}, unnest({field}) AS t(val) "
            f"{where} GROUP BY val"
        )
        for field in ARRAY_FACETS
    }

    hist_sql = (
        f"SELECT floor(val / 0.05) * 0.05 AS bucket_min, "
        f"       floor(val / 0.05) * 0.05 + 0.05 AS bucket_max, "
        f"       count(*) AS cnt "
        f"FROM {TABLE}, unnest(overall_scores) AS t(val) "
        f"{where} GROUP BY bucket_min, bucket_max ORDER BY bucket_min"
    )

    engine = db.get_bind()

    def _run(sql):
        with engine.connect() as conn:
            return conn.execute(text(sql), params).mappings().all()

    with ThreadPoolExecutor(max_workers=4) as pool:
        gs_future = pool.submit(_run, gs_sql)
        arr_futures = {field: pool.submit(_run, sql) for field, sql in arr_sqls.items()}
        hist_future = pool.submit(_run, hist_sql)

        rows = gs_future.result()
        arr_rows_by_field = {field: f.result() for field, f in arr_futures.items()}
        hist_rows = hist_future.result()

    facets = _parse_grouping_sets_rows(rows)

    for field in ARRAY_FACETS:
        buckets = [FacetBucket(key=r["val"], count=r["cnt"]) for r in arr_rows_by_field[field]]
        buckets.sort(key=lambda b: -b.count)
        facets.append(FacetResult(field=field, buckets=buckets))

    histograms = []
    if hist_rows:
        histograms.append(
            HistogramResult(
                field="overall_score",
                buckets=[
                    HistogramBucket(min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"])
                    for r in hist_rows
                ],
            )
        )

    # Total count (from the empty () grouping set)
    total = 0
    for row in rows:
        if all(row[col] is None for col in _GS_COLUMNS):
            total = row["cnt"]
            break

    return FacetsResponse(facets=facets, histograms=histograms, total=total)


def get_facets_preview(request: FacetsPreviewRequest, db: Session) -> FacetsPreviewResponse:
    target = request.target_field
    if target not in _ALL_FACET_FIELDS:
        return FacetsPreviewResponse(target_field=target, previews=[])

    conditions = parse_filters(request.filters)
    if not conditions:
        return _preview_from_cube(target, db)

    where, params = compile_conditions(conditions)
    if target in ARRAY_FACETS:
        return _preview_live_per_value(target, where, params, db)
    return _preview_live_grouped(target, where, params, db)


# ---------------------------------------------------------------------------
# Preview: cube path (unfiltered — sub-millisecond)
# ---------------------------------------------------------------------------


def _preview_from_cube(target: str, db: Session) -> FacetsPreviewResponse:
    rows = (
        db.execute(
            text(
                f"SELECT target_value, facet_field, facet_value, cnt "
                f"FROM {CUBE_TABLE} WHERE target_field = :tf"
            ),
            {"tf": target},
        )
        .mappings()
        .all()
    )

    hist_rows = (
        db.execute(
            text(
                f"SELECT target_value, bucket_min, bucket_max, cnt "
                f"FROM {CUBE_HIST_TABLE} WHERE target_field = :tf"
            ),
            {"tf": target},
        )
        .mappings()
        .all()
    )

    # Group facets by target_value
    facets_by_tv: dict[str, dict[str, list[FacetBucket]]] = {}
    totals: dict[str, int] = {}
    for r in rows:
        tv = r["target_value"]
        if r["facet_field"] == "_total_":
            totals[tv] = r["cnt"]
        else:
            facets_by_tv.setdefault(tv, {}).setdefault(r["facet_field"], []).append(
                FacetBucket(key=r["facet_value"], count=r["cnt"])
            )

    # Group histogram by target_value
    hist_by_tv: dict[str, list[HistogramBucket]] = {}
    for r in hist_rows:
        hist_by_tv.setdefault(r["target_value"], []).append(
            HistogramBucket(min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"])
        )

    # Build ordered facet field list (same order as live queries)
    other_fields = [f for f in _ALL_FACET_FIELDS if f != target]

    previews = []
    for tv in sorted(totals):
        tv_facet_data = facets_by_tv.get(tv, {})
        tv_facets = []
        for field in other_fields:
            buckets = tv_facet_data.get(field, [])
            buckets.sort(key=lambda b: -b.count)
            tv_facets.append(FacetResult(field=field, buckets=buckets))

        tv_histograms = []
        if tv in hist_by_tv:
            tv_histograms.append(HistogramResult(field="overall_score", buckets=hist_by_tv[tv]))

        previews.append(
            FacetsPreviewEntry(
                target_value=tv,
                facets=tv_facets,
                histograms=tv_histograms,
                total=totals.get(tv, 0),
            )
        )

    return FacetsPreviewResponse(target_field=target, previews=previews)


# ---------------------------------------------------------------------------
# Preview: live grouped path (filtered, scalar/bool target)
# ---------------------------------------------------------------------------


def _preview_live_grouped(
    target: str, where: str, params: dict, db: Session
) -> FacetsPreviewResponse:
    """Scalar/bool targets: single unnest only, use GROUPING SETS + concurrent queries."""
    target_col = target
    other_gs_cols = [c for c in _GS_COLUMNS if c != target]
    gs_sets = ", ".join(f"({col})" for col in other_gs_cols)
    col_list = ", ".join(other_gs_cols)
    array_fields = [f for f in ARRAY_FACETS if f != target]

    q1_sql = (
        f"SELECT {target_col} AS target_value, {col_list}, count(*) AS cnt "
        f"FROM {TABLE} {where} "
        f"GROUP BY {target_col}, GROUPING SETS ({gs_sets}, ())"
    )

    arr_parts = []
    for field in array_fields:
        arr_parts.append(
            f"SELECT {target_col} AS target_value, "
            f"'{field}' AS facet_field, t2.val, count(*) AS cnt "
            f"FROM {TABLE}, unnest({field}) AS t2(val) {where} "
            f"GROUP BY {target_col}, t2.val"
        )
    q2_sql = " UNION ALL ".join(arr_parts) if arr_parts else None

    q3_sql = (
        f"SELECT {target_col} AS target_value, "
        f"       floor(t3.val / 0.05) * 0.05 AS bucket_min, "
        f"       floor(t3.val / 0.05) * 0.05 + 0.05 AS bucket_max, "
        f"       count(*) AS cnt "
        f"FROM {TABLE}, unnest(overall_scores) AS t3(val) {where} "
        f"GROUP BY {target_col}, bucket_min, bucket_max ORDER BY bucket_min"
    )

    engine = db.get_bind()

    def _run(sql):
        with engine.connect() as conn:
            return conn.execute(text(sql), params).mappings().all()

    with ThreadPoolExecutor(max_workers=3) as pool:
        f1 = pool.submit(_run, q1_sql)
        f2 = pool.submit(_run, q2_sql) if q2_sql else None
        f3 = pool.submit(_run, q3_sql)
        scalar_rows = f1.result()
        arr_rows = f2.result() if f2 else []
        hist_rows = f3.result()

    # Parse array results
    array_results: dict[str, dict[str, list[FacetBucket]]] = {}
    for r in arr_rows:
        tv = str(r["target_value"])
        array_results.setdefault(tv, {}).setdefault(r["facet_field"], []).append(
            FacetBucket(key=r["val"], count=r["cnt"])
        )

    # Parse histogram
    hist_by_target: dict[str, list[HistogramBucket]] = {}
    for r in hist_rows:
        tv = str(r["target_value"])
        hist_by_target.setdefault(tv, []).append(
            HistogramBucket(min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"])
        )

    # Assemble previews
    total_by_target, target_values = _extract_totals_and_targets(scalar_rows, other_gs_cols)

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
            tv_histograms.append(HistogramResult(field="overall_score", buckets=hist_by_target[tv]))

        if target in BOOL_FACETS:
            false_label, true_label = BOOL_FACETS[target]
            label = true_label if tv == "True" else false_label
        else:
            label = tv

        previews.append(
            FacetsPreviewEntry(
                target_value=label,
                facets=tv_facets,
                histograms=tv_histograms,
                total=total_by_target.get(tv, 0),
            )
        )

    return FacetsPreviewResponse(target_field=target, previews=previews)


# ---------------------------------------------------------------------------
# Preview: live per-value path (filtered, array target — no double unnest)
# ---------------------------------------------------------------------------


def _preview_live_per_value(
    target: str, where: str, params: dict, db: Session
) -> FacetsPreviewResponse:
    """Array targets with filters: use WHERE val = ANY(target) per value.

    Eliminates double unnest — each query does single unnest at most.
    """
    other_gs_cols = [c for c in _GS_COLUMNS if c != target]
    gs_sets = ", ".join(f"({col})" for col in other_gs_cols)
    col_list = ", ".join(other_gs_cols)
    array_fields = [f for f in ARRAY_FACETS if f != target]

    # Q1: scalar/bool facets + totals via single unnest of target (fast)
    q1_sql = (
        f"SELECT target_val AS target_value, {col_list}, count(*) AS cnt "
        f"FROM {TABLE}, unnest({target}) AS t(target_val) {where} "
        f"GROUP BY target_val, GROUPING SETS ({gs_sets}, ())"
    )
    scalar_rows = db.execute(text(q1_sql), params).mappings().all()
    total_by_target, target_values = _extract_totals_and_targets(scalar_rows, other_gs_cols)

    if not target_values:
        return FacetsPreviewResponse(target_field=target, previews=[])

    # Q2+Q3 per target value: WHERE :tv = ANY(target) — single unnest only
    where_any = f"{where} AND :_tv = ANY({target})"
    engine = db.get_bind()

    def _run_for_value(tv: str):
        tv_params = {**params, "_tv": tv}
        with engine.connect() as conn:
            # Array facets
            parts = []
            for field in array_fields:
                parts.append(
                    f"SELECT '{field}' AS facet_field, t2.val, count(*) AS cnt "
                    f"FROM {TABLE}, unnest({field}) AS t2(val) "
                    f"{where_any} GROUP BY t2.val"
                )
            arr_rows = (
                (conn.execute(text(" UNION ALL ".join(parts)), tv_params).mappings().all())
                if parts
                else []
            )

            # Histogram
            hist_rows = (
                conn.execute(
                    text(
                        f"SELECT floor(t3.val / 0.05) * 0.05 AS bucket_min, "
                        f"       floor(t3.val / 0.05) * 0.05 + 0.05 AS bucket_max, "
                        f"       count(*) AS cnt "
                        f"FROM {TABLE}, unnest(overall_scores) AS t3(val) "
                        f"{where_any} "
                        f"GROUP BY bucket_min, bucket_max ORDER BY bucket_min"
                    ),
                    tv_params,
                )
                .mappings()
                .all()
            )

            return arr_rows, hist_rows

    with ThreadPoolExecutor(max_workers=min(len(target_values), 8)) as pool:
        futures = {tv: pool.submit(_run_for_value, tv) for tv in target_values}
        per_value = {tv: f.result() for tv, f in futures.items()}

    # Assemble previews
    previews = []
    for tv in sorted(target_values):
        tv_facets = _parse_preview_grouping_rows(scalar_rows, tv, other_gs_cols)

        arr_rows, hist_rows = per_value[tv]
        arr_by_field: dict[str, list[FacetBucket]] = {}
        for r in arr_rows:
            arr_by_field.setdefault(r["facet_field"], []).append(
                FacetBucket(key=r["val"], count=r["cnt"])
            )
        for field in array_fields:
            buckets = arr_by_field.get(field, [])
            buckets.sort(key=lambda b: -b.count)
            tv_facets.append(FacetResult(field=field, buckets=buckets))

        tv_histograms = []
        if hist_rows:
            tv_histograms.append(
                HistogramResult(
                    field="overall_score",
                    buckets=[
                        HistogramBucket(min=r["bucket_min"], max=r["bucket_max"], count=r["cnt"])
                        for r in hist_rows
                    ],
                )
            )

        previews.append(
            FacetsPreviewEntry(
                target_value=tv,
                facets=tv_facets,
                histograms=tv_histograms,
                total=total_by_target.get(tv, 0),
            )
        )

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
        result.append(
            FacetResult(
                field=field,
                buckets=sorted(buckets_by_field.get(field, []), key=lambda b: -b.count),
            )
        )
    for field in BOOL_FACETS:
        result.append(
            FacetResult(
                field=field,
                buckets=buckets_by_field.get(field, []),
            )
        )
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
            result.append(
                FacetResult(
                    field=field,
                    buckets=sorted(buckets_by_field.get(field, []), key=lambda b: -b.count),
                )
            )
    for field in BOOL_FACETS:
        if field in gs_columns:
            result.append(
                FacetResult(
                    field=field,
                    buckets=buckets_by_field.get(field, []),
                )
            )
    return result

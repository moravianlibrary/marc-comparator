from sqlalchemy import text
from sqlalchemy.orm import Session

TABLE = "catalog_records_analytics"
CUBE_TABLE = "facet_cube"
CUBE_HIST_TABLE = "facet_cube_histogram"

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS catalog_records_analytics (
    id              TEXT PRIMARY KEY,
    base            TEXT NOT NULL,
    system_number   TEXT NOT NULL,
    type_of_record  TEXT,
    bibliographic_level TEXT,
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
    is_processed    BOOLEAN NOT NULL DEFAULT FALSE,
    is_broken       BOOLEAN NOT NULL DEFAULT FALSE,
    has_alternatives BOOLEAN NOT NULL DEFAULT FALSE,
    has_claim       BOOLEAN NOT NULL DEFAULT FALSE,
    claim_needs_review BOOLEAN NOT NULL DEFAULT FALSE,

    authority_link_linkers  TEXT[],
    authority_link_bases    TEXT[],
    link_outcomes           TEXT[],
    link_agencies           TEXT[],
    link_identifiers        TEXT[],

    comparison_bases        TEXT[],
    match_qualities         TEXT[],
    overall_scores          FLOAT[],
    field_explanations      TEXT[],

    validators              TEXT[],
    validation_statuses     TEXT[],
    validation_target_tags  TEXT[],
    validation_reasons      TEXT[],

    reviewed_aspects        TEXT[],
    review_status           TEXT,

    latest_sync             TIMESTAMP,
    latest_transaction      TIMESTAMP,
    processed_at            TIMESTAMP,
    updated_at              TIMESTAMP WITH TIME ZONE
)
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_analytics_base ON catalog_records_analytics (base)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_processed ON catalog_records_analytics (is_processed)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_broken ON catalog_records_analytics (is_broken) WHERE is_broken",
    "CREATE INDEX IF NOT EXISTS idx_analytics_review_status ON catalog_records_analytics (review_status) WHERE review_status != 'ReviewNotNeeded'",
    "CREATE INDEX IF NOT EXISTS idx_analytics_has_alternatives ON catalog_records_analytics (has_alternatives) WHERE has_alternatives",
    "CREATE INDEX IF NOT EXISTS idx_analytics_has_claim ON catalog_records_analytics (has_claim) WHERE has_claim",
    "CREATE INDEX IF NOT EXISTS idx_analytics_claim_needs_review ON catalog_records_analytics (claim_needs_review) WHERE claim_needs_review",
    "CREATE INDEX IF NOT EXISTS idx_analytics_auth_linkers ON catalog_records_analytics USING gin (authority_link_linkers)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_link_agencies ON catalog_records_analytics USING gin (link_agencies)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_link_identifiers ON catalog_records_analytics USING gin (link_identifiers)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_auth_bases ON catalog_records_analytics USING gin (authority_link_bases)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_link_outcomes ON catalog_records_analytics USING gin (link_outcomes)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_comp_bases ON catalog_records_analytics USING gin (comparison_bases)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_match_qual ON catalog_records_analytics USING gin (match_qualities)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_validators ON catalog_records_analytics USING gin (validators)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_val_statuses ON catalog_records_analytics USING gin (validation_statuses)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_val_tags ON catalog_records_analytics USING gin (validation_target_tags)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_val_reasons ON catalog_records_analytics USING gin (validation_reasons)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_field_expl ON catalog_records_analytics USING gin (field_explanations)",
]

CREATE_CUBE_SQL = f"""
CREATE TABLE IF NOT EXISTS {CUBE_TABLE} (
    target_field TEXT NOT NULL,
    target_value TEXT NOT NULL,
    facet_field  TEXT NOT NULL,
    facet_value  TEXT NOT NULL,
    cnt          BIGINT NOT NULL
)
"""

CREATE_CUBE_HIST_SQL = f"""
CREATE TABLE IF NOT EXISTS {CUBE_HIST_TABLE} (
    target_field TEXT NOT NULL,
    target_value TEXT NOT NULL,
    bucket_min   DOUBLE PRECISION NOT NULL,
    bucket_max   DOUBLE PRECISION NOT NULL,
    cnt          BIGINT NOT NULL
)
"""

CREATE_CUBE_INDEXES_SQL = [
    f"CREATE INDEX IF NOT EXISTS idx_cube_target ON {CUBE_TABLE} (target_field)",
    f"CREATE INDEX IF NOT EXISTS idx_cube_hist_target ON {CUBE_HIST_TABLE} (target_field)",
]

# ---------------------------------------------------------------------------
# The SELECT that computes a denormalized row for given record IDs (or all).
# Used by both upsert_records() and rebuild_all().
# ---------------------------------------------------------------------------

_ANALYTICS_SELECT = """
    SELECT
        cr.id,
        cr.base,
        cr.system_number,
        cr.type_of_record,
        cr.bibliographic_level,
        cr.deleted         AS is_deleted,
        (cr.processed_at IS NOT NULL) AS is_processed,
        (cr.processing_error IS NOT NULL) AS is_broken,

        -- Whether linking kept anything behind the answer. A runner-up is
        -- the whole reason the candidates are stored, and until now the
        -- only way to the records that have one was to read the rows one
        -- at a time: `rank` is on the link, not on the record.
        EXISTS (
            SELECT 1 FROM authority_links alt
            WHERE alt.main_record_id = cr.id AND alt.rank > 0
        ) AS has_alternatives,

        -- Whether a cataloguer has ruled on this record. The answer a
        -- person asserted and the answer a linker computed are not the
        -- same kind of thing, and a list that cannot tell them apart
        -- invites re-deciding what somebody already decided.
        EXISTS (
            SELECT 1 FROM link_claims lc WHERE lc.main_record_id = cr.id
        ) AS has_claim,

        -- Whether the evidence has moved against one of those rulings
        -- since it was made. The claim still decides the answer; this
        -- only asks for a second look, and it is the one worklist the
        -- claim feature exists to produce.
        EXISTS (
            SELECT 1 FROM link_claims lc2
            WHERE lc2.main_record_id = cr.id AND lc2.needs_review
        ) AS claim_needs_review,

        array_agg(DISTINCT al.linker)
            FILTER (WHERE al.linker IS NOT NULL)            AS authority_link_linkers,
        array_agg(DISTINCT al.base)
            FILTER (WHERE al.base IS NOT NULL)              AS authority_link_bases,

        -- The answer for each base, whatever it says — which is the column
        -- that tells the records linking failed on from the ones it linked.
        -- Answers only: a runner-up is not an outcome, and including the
        -- `Rejected` rows would put a value in this facet that means
        -- something else entirely and stop the buckets partitioning the
        -- records. A subquery rather than a second join, which would
        -- multiply the rows every array_agg above is computed over.
        (SELECT array_agg(DISTINCT al2.outcome)
         FROM authority_links al2
         WHERE al2.main_record_id = cr.id AND al2.rank = 0
        ) AS link_outcomes,

        -- Who catalogued the record on the other end of each accepted link.
        -- A subquery for the same reason as link_outcomes: a second join
        -- would multiply the rows every array_agg above is computed over.
        (SELECT array_agg(DISTINCT auth.cataloguing_agency)
         FROM authority_links al3
         JOIN catalog_records auth ON auth.id = al3.authority_record_id
         WHERE al3.main_record_id = cr.id
           AND al3.rank = 0 AND al3.outcome = 'Linked'
           AND auth.cataloguing_agency IS NOT NULL
        ) AS link_agencies,

        -- Which identifier retrieved each attempt, where one did. Every rank,
        -- not only the answer: "we refused a pair that shares a national
        -- bibliography number" is exactly the thing worth going to look at.
        (SELECT array_agg(DISTINCT al4.matched_identifier)
         FROM authority_links al4
         WHERE al4.main_record_id = cr.id AND al4.matched_identifier IS NOT NULL
        ) AS link_identifiers,

        array_agg(DISTINCT cmp.base)
            FILTER (WHERE cmp.base IS NOT NULL)             AS comparison_bases,
        -- The band the comparator recorded, not a second opinion about it.
        -- Two thresholds were written out here in SQL and again in the entity
        -- that reads the same column, against a comparator free to move them.
        array_agg(DISTINCT cmp.result->>'quality')
            FILTER (WHERE cmp.result->>'quality' IS NOT NULL)       AS match_qualities,
        array_agg((cmp.result->>'overall_score')::float)
            FILTER (WHERE cmp.result->>'overall_score' IS NOT NULL) AS overall_scores,

        (SELECT array_agg(DISTINCT expl)
         FROM comparisons c2,
              jsonb_array_elements(c2.result->'field_results') fr,
              jsonb_extract_path_text(fr, 'explanation') expl
         WHERE c2.main_record_id = cr.id AND expl IS NOT NULL
        ) AS field_explanations,

        array_agg(DISTINCT v.validator)
            FILTER (WHERE v.validator IS NOT NULL)                  AS validators,
        array_agg(DISTINCT (v.validator || ':' || (v.result->>'status')))
            FILTER (WHERE v.result->>'status' IS NOT NULL)         AS validation_statuses,
        array_agg(DISTINCT (v.result->'target'->>'tag'))
            FILTER (WHERE v.result->'target'->>'tag' IS NOT NULL)  AS validation_target_tags,
        array_agg(DISTINCT (v.validator || ':' || (v.result->>'reason')))
            FILTER (WHERE v.result->>'reason' IS NOT NULL)         AS validation_reasons,

        array_agg(DISTINCT rr.aspect_name)
            FILTER (WHERE rr.id IS NOT NULL)                       AS reviewed_aspects,
        CASE
            -- A record nobody could read has no comparisons and no validations,
            -- so every branch below would call it ReviewNotNeeded. That is the
            -- reading that made a broken record look clean; it has no review
            -- status at all, which is what the ORM's `state` now says too.
            WHEN cr.processing_error IS NOT NULL THEN NULL
            WHEN NOT EXISTS (
                SELECT 1 FROM comparisons cmp2
                WHERE cmp2.main_record_id = cr.id
                  AND cmp2.result->>'quality' <> 'Excellent'
            ) AND NOT EXISTS (
                SELECT 1 FROM validations v2
                WHERE v2.catalog_record_id = cr.id
                  AND v2.result->>'status' NOT IN ('Valid', 'AdditionalInfo')
            )
            THEN 'ReviewNotNeeded'
            WHEN NOT EXISTS (
                SELECT 1 FROM (
                    SELECT cmp2.comparator AS aspect FROM comparisons cmp2
                    WHERE cmp2.main_record_id = cr.id
                      AND cmp2.result->>'quality' <> 'Excellent'
                    UNION
                    SELECT v2.validator FROM validations v2
                    WHERE v2.catalog_record_id = cr.id
                      AND v2.result->>'status' NOT IN ('Valid', 'AdditionalInfo')
                ) nr
                WHERE nr.aspect NOT IN (
                    SELECT rr2.aspect_name FROM record_reviews rr2
                    WHERE rr2.record_id = cr.id AND rr2.status = 'current'
                )
            )
            THEN 'Reviewed'
            WHEN EXISTS (
                SELECT 1 FROM record_reviews rr2
                WHERE rr2.record_id = cr.id AND rr2.status = 'current'
                AND rr2.aspect_name IN (
                    SELECT cmp2.comparator FROM comparisons cmp2
                    WHERE cmp2.main_record_id = cr.id
                      AND cmp2.result->>'quality' <> 'Excellent'
                    UNION
                    SELECT v2.validator FROM validations v2
                    WHERE v2.catalog_record_id = cr.id
                      AND v2.result->>'status' NOT IN ('Valid', 'AdditionalInfo')
                )
            )
            THEN 'PartiallyReviewed'
            ELSE 'Unreviewed'
        END AS review_status,

        cr.latest_sync,
        cr.latest_transaction,
        cr.processed_at,
        cr.updated_at
    FROM catalog_records cr
    -- Scoped to the accepted links, matching `CatalogRecord.authority_links`:
    -- the linker and base facets mean "linked by", and a gap row would put
    -- the linker that failed among the linkers that succeeded.
    LEFT JOIN authority_links al
           ON al.main_record_id = cr.id AND al.rank = 0 AND al.outcome = 'Linked'
    LEFT JOIN comparisons cmp ON cmp.main_record_id = cr.id
    LEFT JOIN validations v ON v.catalog_record_id = cr.id
    LEFT JOIN record_reviews rr ON rr.record_id = cr.id AND rr.status = 'current'
    WHERE cr.source_type = 'Main'
"""

_ANALYTICS_GROUP_BY = "GROUP BY cr.id"

#: The columns `_ANALYTICS_SELECT` produces, in its order.
#:
#: Naming them is not decoration. `INSERT INTO t SELECT ...` matches by
#: position, and a column added by ADD_COLUMNS_SQL lands at the end of an
#: existing table while sitting mid-list in CREATE_TABLE_SQL. The two
#: disagree from then on, and the insert quietly files each value one
#: column to the left of where it belongs.
_ANALYTICS_COLUMNS = """
    id, base, system_number, type_of_record, bibliographic_level,
    is_deleted, is_processed, is_broken,
    has_alternatives, has_claim, claim_needs_review,
    authority_link_linkers, authority_link_bases, link_outcomes, link_agencies,
    link_identifiers,
    comparison_bases, match_qualities, overall_scores, field_explanations,
    validators, validation_statuses, validation_target_tags, validation_reasons,
    reviewed_aspects, review_status,
    latest_sync, latest_transaction, processed_at, updated_at
"""


#: Columns added to the analytics table after it first shipped.
#:
#: The table is derived, not authoritative, so it is created rather than
#: migrated — but CREATE TABLE IF NOT EXISTS is a no-op where one already
#: exists, which would leave an older deployment without the new column and
#: every query naming it broken. Each entry is an ALTER that is safe to repeat.
ADD_COLUMNS_SQL = [
    "ALTER TABLE catalog_records_analytics "
    "ADD COLUMN IF NOT EXISTS is_broken BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE catalog_records_analytics ADD COLUMN IF NOT EXISTS link_outcomes TEXT[]",
    "ALTER TABLE catalog_records_analytics ADD COLUMN IF NOT EXISTS link_agencies TEXT[]",
    "ALTER TABLE catalog_records_analytics ADD COLUMN IF NOT EXISTS link_identifiers TEXT[]",
    "ALTER TABLE catalog_records_analytics "
    "ADD COLUMN IF NOT EXISTS has_alternatives BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE catalog_records_analytics "
    "ADD COLUMN IF NOT EXISTS has_claim BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE catalog_records_analytics "
    "ADD COLUMN IF NOT EXISTS claim_needs_review BOOLEAN NOT NULL DEFAULT FALSE",
]


def init_analytics_table(db: Session) -> None:
    """Create the analytics table, cube tables, and indexes if they don't exist."""
    db.execute(text(CREATE_TABLE_SQL))
    for alter_sql in ADD_COLUMNS_SQL:
        db.execute(text(alter_sql))
    for idx_sql in CREATE_INDEXES_SQL:
        db.execute(text(idx_sql))
    db.execute(text(CREATE_CUBE_SQL))
    db.execute(text(CREATE_CUBE_HIST_SQL))
    for idx_sql in CREATE_CUBE_INDEXES_SQL:
        db.execute(text(idx_sql))
    db.commit()


def upsert_records(db: Session, record_ids: list[str]) -> None:
    """Upsert specific records into the analytics table.
    Use after review create/delete or single-record changes."""
    if not record_ids:
        return
    db.execute(
        text(f"""
        INSERT INTO {TABLE} ({_ANALYTICS_COLUMNS}) {_ANALYTICS_SELECT}
            AND cr.id = ANY(:ids)
            {_ANALYTICS_GROUP_BY}
        ON CONFLICT (id) DO UPDATE SET
            base = EXCLUDED.base,
            system_number = EXCLUDED.system_number,
            type_of_record = EXCLUDED.type_of_record,
            bibliographic_level = EXCLUDED.bibliographic_level,
            is_deleted = EXCLUDED.is_deleted,
            is_processed = EXCLUDED.is_processed,
            is_broken = EXCLUDED.is_broken,
            has_alternatives = EXCLUDED.has_alternatives,
            has_claim = EXCLUDED.has_claim,
            claim_needs_review = EXCLUDED.claim_needs_review,
            authority_link_linkers = EXCLUDED.authority_link_linkers,
            authority_link_bases = EXCLUDED.authority_link_bases,
            link_outcomes = EXCLUDED.link_outcomes,
            link_agencies = EXCLUDED.link_agencies,
            link_identifiers = EXCLUDED.link_identifiers,
            comparison_bases = EXCLUDED.comparison_bases,
            match_qualities = EXCLUDED.match_qualities,
            overall_scores = EXCLUDED.overall_scores,
            field_explanations = EXCLUDED.field_explanations,
            validators = EXCLUDED.validators,
            validation_statuses = EXCLUDED.validation_statuses,
            validation_target_tags = EXCLUDED.validation_target_tags,
            validation_reasons = EXCLUDED.validation_reasons,
            reviewed_aspects = EXCLUDED.reviewed_aspects,
            review_status = EXCLUDED.review_status,
            latest_sync = EXCLUDED.latest_sync,
            latest_transaction = EXCLUDED.latest_transaction,
            processed_at = EXCLUDED.processed_at,
            updated_at = EXCLUDED.updated_at
    """),
        {"ids": record_ids},
    )
    db.commit()


def rebuild_all(db: Session) -> None:
    """Full rebuild of the analytics table and facet cube."""
    db.execute(text(f"TRUNCATE {TABLE}"))
    db.execute(
        text(f"""
        INSERT INTO {TABLE} ({_ANALYTICS_COLUMNS}) {_ANALYTICS_SELECT}
            {_ANALYTICS_GROUP_BY}
    """)
    )
    db.commit()
    rebuild_cube(db)


# ---------------------------------------------------------------------------
# Facet co-occurrence cube
# ---------------------------------------------------------------------------

#: Which analytics columns are facets, and of what shape.
#:
#: Defined here rather than in ``catalog_records.facets`` because both
#: modules need them and this is the one they can both see: the cube is
#: built from these lists and the live queries read the same columns. They
#: used to be written out in each module with a comment asking the next
#: person to keep them in step, and they drifted — ``link_agencies`` was
#: added to the live list alone, so the facet was computed for a filtered
#: query and silently missing from the unfiltered one, which is the view
#: almost everybody opens first.
SCALAR_FACETS = ["base", "type_of_record", "bibliographic_level", "review_status"]

#: Boolean columns, mapped to the labels their two buckets carry.
BOOL_FACETS = {
    "is_deleted": ("Active", "Deleted"),
    "is_processed": ("Unprocessed", "Processed"),
    "is_broken": ("Readable", "Broken"),
    "has_alternatives": ("Single candidate", "Has alternatives"),
    "has_claim": ("Machine answer", "Cataloguer's answer"),
    "claim_needs_review": ("Claim holds", "Claim needs review"),
}
ARRAY_FACETS = [
    "authority_link_linkers",
    "authority_link_bases",
    "link_outcomes",
    "link_agencies",
    "link_identifiers",
    "comparison_bases",
    "match_qualities",
    "validators",
    "validation_statuses",
    "validation_target_tags",
    "validation_reasons",
    "field_explanations",
]
ALL_FACET_FIELDS = SCALAR_FACETS + list(BOOL_FACETS.keys()) + ARRAY_FACETS


def _quoted(label: str) -> str:
    """A bucket label as a SQL string literal.

    The cube's SQL is assembled by hand around these labels, so one
    carrying an apostrophe would close the literal early and break the
    statement. They are ours, not anybody's input, but writing a label
    should not mean knowing that.
    """

    return "'" + label.replace("'", "''") + "'"


def _target_sql(field: str) -> tuple[str, str, str]:
    """Return (select_expr, from_extra, group_col) for a target field."""
    if field in ARRAY_FACETS:
        return "tv::text", f", unnest({field}) AS _t(tv)", "tv"
    if field in BOOL_FACETS:
        fl, tl = BOOL_FACETS[field]
        return f"CASE WHEN {field} THEN {_quoted(tl)} ELSE {_quoted(fl)} END", "", field
    return f"{field}::text", "", field


def _facet_sql(field: str) -> tuple[str, str, str]:
    """Return (select_expr, from_extra, group_col) for a facet field."""
    if field in ARRAY_FACETS:
        return "fv::text", f", unnest({field}) AS _f(fv)", "fv"
    if field in BOOL_FACETS:
        fl, tl = BOOL_FACETS[field]
        return f"CASE WHEN {field} THEN {_quoted(tl)} ELSE {_quoted(fl)} END", "", field
    return f"{field}::text", "", field


def _build_cube_sql_for_target(target: str) -> str:
    """Build INSERT ... SELECT UNION ALL for one target field (co-occurrences + totals)."""
    t_expr, t_from, t_group = _target_sql(target)
    t_lit = f"'{target}'"

    # NULL filter for scalar targets (array/bool can't be NULL in practice)
    t_where = f" WHERE {target} IS NOT NULL" if target in SCALAR_FACETS else ""

    branches = []

    # Totals per target value
    branches.append(
        f"SELECT {t_lit} AS target_field, {t_expr} AS target_value, "
        f"'_total_' AS facet_field, '_total_' AS facet_value, count(*) AS cnt "
        f"FROM {TABLE}{t_from}{t_where} GROUP BY {t_group}"
    )

    for facet in ALL_FACET_FIELDS:
        if facet == target:
            continue
        f_expr, f_from, f_group = _facet_sql(facet)
        f_lit = f"'{facet}'"

        # For scalar facets, filter NULLs
        where_parts = []
        if target in SCALAR_FACETS:
            where_parts.append(f"{target} IS NOT NULL")
        if facet in SCALAR_FACETS:
            where_parts.append(f"{facet} IS NOT NULL")
        where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        branches.append(
            f"SELECT {t_lit} AS target_field, {t_expr} AS target_value, "
            f"{f_lit} AS facet_field, {f_expr} AS facet_value, count(*) AS cnt "
            f"FROM {TABLE}{t_from}{f_from}{where} "
            f"GROUP BY {t_group}, {f_group}"
        )

    return f"INSERT INTO {CUBE_TABLE} " + " UNION ALL ".join(branches)


#: Width of one overall-score histogram bucket. Thirty buckets across the 0-15
#: match scale, which is the resolution the 0.05 buckets of the old 0-1 scale
#: gave — and it divides the scale evenly, so no bucket straddles a band edge.
SCORE_BUCKET = 0.5


def _build_cube_hist_sql_for_target(target: str) -> str:
    """Build INSERT ... SELECT for histogram buckets of one target field."""
    t_expr, t_from, t_group = _target_sql(target)
    t_lit = f"'{target}'"

    hist_from = ", unnest(overall_scores) AS _h(val)"
    t_where = f" WHERE {target} IS NOT NULL" if target in SCALAR_FACETS else ""

    return (
        f"INSERT INTO {CUBE_HIST_TABLE} "
        f"SELECT {t_lit} AS target_field, {t_expr} AS target_value, "
        f"floor(_h.val / {SCORE_BUCKET}) * {SCORE_BUCKET} AS bucket_min, "
        f"floor(_h.val / {SCORE_BUCKET}) * {SCORE_BUCKET} + {SCORE_BUCKET} AS bucket_max, "
        f"count(*) AS cnt "
        f"FROM {TABLE}{t_from}{hist_from}{t_where} "
        f"GROUP BY {t_group}, bucket_min, bucket_max"
    )


#: Temporary long-form table the cube is aggregated from, one row per
#: (record, facet field, facet value).
_PAIRS_TABLE = "facet_pairs"


def _build_pairs_sql() -> str:
    """Read every facet value of every record once, as (id, field, value).

    A field contributes what it would contribute to a group by on itself: a
    scalar its value unless null, a boolean its label, an array one row per
    element — repeats included, so a value appearing twice in one record counts
    twice, exactly as unnesting in place does.
    """

    branches = []
    for field in ALL_FACET_FIELDS:
        if field in ARRAY_FACETS:
            branches.append(
                f"SELECT id, '{field}' AS field, v::text AS value "
                f"FROM {TABLE}, unnest({field}) AS _u(v)"
            )
        elif field in BOOL_FACETS:
            false_label, true_label = BOOL_FACETS[field]
            branches.append(
                f"SELECT id, '{field}' AS field, "
                f"CASE WHEN {field} THEN {_quoted(true_label)} "
                f"ELSE {_quoted(false_label)} END AS value "
                f"FROM {TABLE}"
            )
        else:
            branches.append(
                f"SELECT id, '{field}' AS field, {field}::text AS value "
                f"FROM {TABLE} WHERE {field} IS NOT NULL"
            )
    return f"CREATE TEMP TABLE {_PAIRS_TABLE} ON COMMIT DROP AS " + " UNION ALL ".join(branches)


def rebuild_cube(db: Session) -> None:
    """Rebuild the facet co-occurrence cube from the analytics table.

    Every pair of facet fields needs a count, and asking for them one pair at a
    time means fifteen fields squared — two hundred and twenty-five scans of
    the analytics table, all of them cached and all of them re-reading the same
    hundred and fifty thousand rows. Reading each record's facet values once
    into long form and joining that to itself gets the same cube, byte for
    byte, from fifteen scans: measured at 17.2 s against 5.1 s.

    The histograms still go per target, since each needs that target's own
    scores; together they are a twentieth of the cost.
    """

    db.execute(text(f"TRUNCATE {CUBE_TABLE}"))
    db.execute(text(f"TRUNCATE {CUBE_HIST_TABLE}"))

    db.execute(text(f"DROP TABLE IF EXISTS {_PAIRS_TABLE}"))
    db.execute(text(_build_pairs_sql()))
    # Without statistics the planner cannot size the self-join and picks badly.
    db.execute(text(f"ANALYZE {_PAIRS_TABLE}"))

    columns = "target_field, target_value, facet_field, facet_value, cnt"
    db.execute(
        text(f"""
        INSERT INTO {CUBE_TABLE} ({columns})
        SELECT field, value, '_total_', '_total_', count(*)
        FROM {_PAIRS_TABLE} GROUP BY 1, 2
    """)
    )
    db.execute(
        text(f"""
        INSERT INTO {CUBE_TABLE} ({columns})
        SELECT t.field, t.value, f.field, f.value, count(*)
        FROM {_PAIRS_TABLE} t JOIN {_PAIRS_TABLE} f USING (id)
        WHERE t.field <> f.field
        GROUP BY 1, 2, 3, 4
    """)
    )

    for target in ALL_FACET_FIELDS:
        db.execute(text(_build_cube_hist_sql_for_target(target)))

    # The pairs table is ON COMMIT DROP, so this is also what clears it.
    db.commit()

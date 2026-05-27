from sqlalchemy import text
from sqlalchemy.orm import Session

TABLE = "catalog_records_analytics"

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

    authority_link_linkers  TEXT[],
    authority_link_bases    TEXT[],

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
    "CREATE INDEX IF NOT EXISTS idx_analytics_base ON catalog_records_analytics USING brin (base)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_processed ON catalog_records_analytics USING brin (is_processed)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_review_status ON catalog_records_analytics (review_status) WHERE review_status != 'ReviewNotNeeded'",
    "CREATE INDEX IF NOT EXISTS idx_analytics_auth_linkers ON catalog_records_analytics USING gin (authority_link_linkers)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_auth_bases ON catalog_records_analytics USING gin (authority_link_bases)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_comp_bases ON catalog_records_analytics USING gin (comparison_bases)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_match_qual ON catalog_records_analytics USING gin (match_qualities)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_validators ON catalog_records_analytics USING gin (validators)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_val_statuses ON catalog_records_analytics USING gin (validation_statuses)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_val_tags ON catalog_records_analytics USING gin (validation_target_tags)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_val_reasons ON catalog_records_analytics USING gin (validation_reasons)",
    "CREATE INDEX IF NOT EXISTS idx_analytics_field_expl ON catalog_records_analytics USING gin (field_explanations)",
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

        array_agg(DISTINCT al.linker)
            FILTER (WHERE al.linker IS NOT NULL)            AS authority_link_linkers,
        array_agg(DISTINCT al.base)
            FILTER (WHERE al.base IS NOT NULL)              AS authority_link_bases,

        array_agg(DISTINCT cmp.base)
            FILTER (WHERE cmp.base IS NOT NULL)             AS comparison_bases,
        array_agg(DISTINCT CASE
            WHEN (cmp.result->>'overall_score')::float >= 0.9 THEN 'Excellent'
            WHEN (cmp.result->>'overall_score')::float >= 0.7 THEN 'Moderate'
            ELSE 'Poor'
        END)
            FILTER (WHERE cmp.result->>'overall_score' IS NOT NULL) AS match_qualities,
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
        array_agg(DISTINCT (v.result->>'status'))
            FILTER (WHERE v.result->>'status' IS NOT NULL)         AS validation_statuses,
        array_agg(DISTINCT (v.result->'target'->>'tag'))
            FILTER (WHERE v.result->'target'->>'tag' IS NOT NULL)  AS validation_target_tags,
        array_agg(DISTINCT (v.result->>'reason'))
            FILTER (WHERE v.result->>'reason' IS NOT NULL)         AS validation_reasons,

        array_agg(DISTINCT rr.aspect_name)
            FILTER (WHERE rr.id IS NOT NULL)                       AS reviewed_aspects,
        CASE
            WHEN NOT EXISTS (
                SELECT 1 FROM comparisons cmp2
                WHERE cmp2.main_record_id = cr.id
                  AND (cmp2.result->>'overall_score')::float < 0.9
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
                      AND (cmp2.result->>'overall_score')::float < 0.9
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
                      AND (cmp2.result->>'overall_score')::float < 0.9
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
    LEFT JOIN authority_links al ON al.main_record_id = cr.id
    LEFT JOIN comparisons cmp ON cmp.main_record_id = cr.id
    LEFT JOIN validations v ON v.catalog_record_id = cr.id
    LEFT JOIN record_reviews rr ON rr.record_id = cr.id AND rr.status = 'current'
    WHERE cr.source_type = 'Main'
"""


def init_analytics_table(db: Session) -> None:
    """Create the analytics table and indexes if they don't exist."""
    db.execute(text(CREATE_TABLE_SQL))
    for idx_sql in CREATE_INDEXES_SQL:
        db.execute(text(idx_sql))
    db.commit()


def upsert_records(db: Session, record_ids: list[str]) -> None:
    """Upsert specific records into the analytics table.
    Use after review create/delete or single-record changes."""
    if not record_ids:
        return
    db.execute(text(f"""
        INSERT INTO {TABLE} {_ANALYTICS_SELECT}
            AND cr.id = ANY(:ids)
            GROUP BY cr.id
        ON CONFLICT (id) DO UPDATE SET
            base = EXCLUDED.base,
            system_number = EXCLUDED.system_number,
            type_of_record = EXCLUDED.type_of_record,
            bibliographic_level = EXCLUDED.bibliographic_level,
            is_deleted = EXCLUDED.is_deleted,
            is_processed = EXCLUDED.is_processed,
            authority_link_linkers = EXCLUDED.authority_link_linkers,
            authority_link_bases = EXCLUDED.authority_link_bases,
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
    """), {"ids": record_ids})
    db.commit()


def rebuild_all(db: Session) -> None:
    """Full rebuild of the analytics table. Use as maintenance fallback."""
    db.execute(text(f"TRUNCATE {TABLE}"))
    db.execute(text(f"""
        INSERT INTO {TABLE} {_ANALYTICS_SELECT}
            GROUP BY cr.id
    """))
    db.commit()

CREATE DATABASE IF NOT EXISTS marc;

CREATE TABLE IF NOT EXISTS marc.catalog_records_analytics (
    id String,
    base LowCardinality(String),
    system_number String,
    type_of_record LowCardinality(String),
    bibliographic_level LowCardinality(String),

    is_deleted UInt8,
    is_hidden UInt8,
    is_processed UInt8,

    authority_link_linkers Array(LowCardinality(String)),
    authority_link_bases Array(LowCardinality(String)),

    comparators Array(LowCardinality(String)),
    comparison_bases Array(LowCardinality(String)),
    match_qualities Array(LowCardinality(String)),
    overall_scores Array(Float64),
    field_explanations Array(LowCardinality(String)),

    validators Array(LowCardinality(String)),
    validation_statuses Array(LowCardinality(String)),
    validation_target_tags Array(LowCardinality(String)),

    latest_sync Nullable(DateTime64(3)),
    latest_transaction Nullable(DateTime64(3)),
    processed_at Nullable(DateTime64(3)),

    updated_at DateTime64(3)
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (base, id);

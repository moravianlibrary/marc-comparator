# Persistent data model

The SQLAlchemy entities in `app/entities/` and Alembic migrations in
`app/migrations/versions/` define the schema. This page describes relationships
that matter to application behavior; it is not a column-by-column migration
reference.

- `catalog_records` represents bibliographic and accepted authority records.
  MARC bytes are stored by base and sector in `marc_sectors`, with
  `marc_record_index` locating each record within a sector. A candidate that
  has not been accepted does not need a catalog record row.
- `comparisons` has one result per main record, comparator and target base.
  Its `other_record_id` points to a catalog record. Scores in its result use
  the 0–15 match scale and store the comparator's quality band.
- `validations` stores validator findings. The Kramerius report groups findings
  by reason and emits repair, normalization, deletion and review artifacts.
- `authority_links` has key `(main_record_id, base, rank)`. Rank 0 is the
  answer for that source record and target base; it can be a `Linked` record
  or an explicit gap outcome. Higher ranks hold retained alternatives.
  Candidate natural keys are `(authority_base, authority_sysno)`, and
  `candidate_count` can exceed the retained row count. See
  [linking and review](linking-review.md).
- `link_claims` records cataloguer verdicts keyed by main record, target base
  and candidate natural key. A `SameWork` claim can override the machine
  answer; `NotSameWork` rejects a candidate. `needs_review` is advisory.
- `record_reviews` stores review history for comparison and validation
  aspects. A changed result can mark a review outdated without removing it.
- `tasks` records background work, status, progress and logs. `settings` stores
  system and record-tool settings; saved settings must be checked during
  migrations because changing a code default does not alter an existing row.
- `catalog_records_analytics` is a maintained PostgreSQL table for search and
  facets, including link outcomes, alternatives, claims, review flags,
  comparison scores and validation reasons. It is a maintained PostgreSQL
  table. Its DDL and rebuild logic live in `app/catalog_records/analytics.py`.

For exact column types, constraints and current defaults, inspect the entity
classes and migrations. The source of truth for filter fields is
`app/catalog_records/models.py` and for API shapes is the running FastAPI
OpenAPI schema at `/openapi.json`.

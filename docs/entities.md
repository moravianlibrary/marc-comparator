# Database Entities

## Entity Relationship Diagram

[`diagrams/entity-relationships.puml`](diagrams/entity-relationships.puml)

---

## users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | User ID |
| email | String | UNIQUE, NOT NULL | Login email |
| first_name | String | NOT NULL | |
| last_name | String | NOT NULL | |
| password_hash | String | NOT NULL | bcrypt hash |

**Relationships:** `roles` (many-to-many via `user_roles`)

---

## roles

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK | |
| name | String | UNIQUE, NOT NULL | Role name |
| permissions | JSONB | NOT NULL | Array of permission strings |
| immutable | Boolean | default False | Cannot modify permissions |
| protected | Boolean | default False | Cannot rename/delete |

**Default roles:**
- **Admin** (immutable, protected): all permissions
- **Guest** (protected): ReadRecords only

**Permissions** (with dependency chain):
```
ReadRecords
├── AddRecords
│   └── SyncRecordsFromCatalog (also requires ManageTasks)
├── ReviewRecords
│   └── ManageReviews
├── ProcessRecords
│   └── ManageTasks
│       └── ManageAllTasks
├── RunPartialRecordTasks
│   └── ManageTasks
└── (standalone)
    ├── ManageAccessControl
    ├── ManageAppSettings
    └── ManageTaskSettings (also requires ManageTasks)
```

---

## catalog_records

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String | PK | `{base}-{system_number}` |
| base | String | NOT NULL | Catalog base (e.g., "MZK01") |
| system_number | String | NOT NULL | Record identifier within base |
| title | String | nullable | Extracted from MARC 245$a |
| authors | ARRAY(String) | default [] | Extracted from MARC 100$a |
| latest_sync | TIMESTAMP | NOT NULL, default now | Last sync from catalog |
| deleted | Boolean | default False | Marked deleted in catalog |
| processed_at | TIMESTAMP | nullable | When full pipeline last ran |
| source_type | String | default "Main" | "Main" or "AuthorityLinker" |
| source_name | String | nullable | Linker name if AuthorityLinker |
| updated_at | TIMESTAMP(tz) | auto-updated | |
| type_of_record | String | nullable | MARC leader byte 6 |
| bibliographic_level | String | nullable | MARC leader byte 7 |
| latest_transaction | TIMESTAMP | nullable | MARC 005 field |
| search_text | String | nullable | Denormalized: sys_num + title + subtitle + authors |
| search_vector | TSVECTOR | | GIN-indexed full-text search |

**Indexes:**
- `idx_catalog_records_search_vector` (GIN)
- `idx_catalog_records_updated_at`

**Relationships:**
- `authority_links` → AuthorityLink (via main_record_id)
- `comparisons` → Comparison (via main_record_id)
- `validations` → Validation (via catalog_record_id)
- `reviews` → RecordReview (via record_id)

**Computed `state` property** (not stored):
- Active/Deleted (from `deleted`)
- Processed/Unprocessed (from `processed_at`)
- ReviewNotNeeded/Reviewed/PartiallyReviewed/Unreviewed (from reviews vs aspects needing review)

---

## comparisons

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| main_record_id | String | PK, FK→catalog_records | Source record |
| comparator | String | PK | Comparator name |
| base | String | PK | Target base |
| other_record_id | String | FK→catalog_records, NOT NULL | Matched record |
| result | JSONB | NOT NULL | `RecordComparisonResult` |
| updated_at | TIMESTAMP | auto-updated | |

**Result JSONB structure:**
```json
{
  "overall_score": 0.85,
  "match_quality": "Moderate",
  "summary": "...",
  "field_results": [
    {
      "tag": "245",
      "score": 0.9,
      "explanation": "NonStandardized",
      "details": "...",
      "value_a": "...",
      "value_b": "...",
      "subfield_results": [
        { "code": "a", "score": 1.0, "value_a": "...", "value_b": "...", "explanation": "Identical" }
      ]
    }
  ]
}
```

---

## validations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, autoincrement | |
| catalog_record_id | String | FK→catalog_records, NOT NULL | Validated record |
| validator | String | NOT NULL | Validator name (e.g., "kramerius-links") |
| result | JSONB | NOT NULL | `ValidationResult` |
| updated_at | TIMESTAMP | auto-updated | |

**Result JSONB structure:**
```json
{
  "target": { "tag": "856", "codes": ["u"] },
  "status": "Invalid",
  "reason": "BrokenLink",
  "details": "HTTP 404 for https://...",
  "details_params": { "url": "https://..." },
  "hint": "Check the URL or remove the field"
}
```

**Status values:** Valid, ForReview, Invalid, AdditionalInfo

---

## authority_links

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| main_record_id | String | PK, FK→catalog_records | Source record |
| linker | String | PK | Linker name (e.g., "KnihovnyCz") |
| base | String | PK | Target base |
| authority_record_id | String | FK→catalog_records, NOT NULL | Linked authority record |
| confidence | Float | nullable | Match confidence score |
| updated_at | TIMESTAMP | auto-updated | |

---

## record_reviews

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| record_id | String | FK→catalog_records, NOT NULL | Reviewed record |
| aspect_name | String | NOT NULL | Comparator or validator name |
| note | Text | nullable | Reviewer's note |
| reviewed_by | UUID | FK→users, NOT NULL | |
| reviewed_at | TIMESTAMP | default now | |
| status | String | default "current" | current, superseded, outdated |

**Index:** `ix_record_reviews_lookup` (record_id, aspect_name, status)

**Status transitions:**
- `current` → `superseded`: when a new review is created for the same aspect
- `current` → `outdated`: when underlying comparison/validation results change
- Reviews are never deleted, only status-transitioned for audit trail

---

## tasks

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| task_id | UUID | PK, default gen_random_uuid | |
| name | String(255) | NOT NULL | Display name |
| type | Enum(TaskType) | NOT NULL | Task type enum |
| status | Enum(TaskStatus) | default Pending | Pending, Started, Success, Failure, Revoked |
| severity | Enum(TaskSeverity) | default Info | Info, Warning, Error, Critical |
| created_by | UUID | FK→users, NOT NULL | |
| created_at | TIMESTAMP | default now | |
| started_at | TIMESTAMP | nullable | |
| finished_at | TIMESTAMP | nullable | |
| data | JSON | nullable | Task-specific input parameters |
| progress | Float | default 0.0 | 0.0 to 1.0 |
| traceback | Text | nullable | Task execution logs |

**TaskType values:**
- Record operations: FetchRecord, FetchBatchOfRecords, SyncRecords, ProcessRecords
- Partial tasks: ValidateRecords, LinkRecordsToAuthorities, CompareRecords
- Maintenance: DeleteTasks, RefreshAnalytics, CleanupStaleLocks, CompactSectors, RebuildSearchVectors

---

## marc_sectors

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| base | String | PK | Catalog base |
| sector_id | Integer | PK | Sector number |
| data | LargeBinary | NOT NULL, STORAGE EXTERNAL | zstd-compressed MARC blob |
| record_count | SmallInteger | default 0 | Active records in sector |

Sectors store up to 1000 MARC records each. `STORAGE EXTERNAL` disables TOAST compression (data is already zstd-compressed).

---

## marc_record_index

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| base | String | PK | Catalog base |
| system_number | String | PK | Record identifier |
| sector_id | Integer | NOT NULL | FK→marc_sectors |
| offset_in_sector | Integer | NOT NULL | Byte offset within decompressed sector |
| record_length | Integer | NOT NULL | MARC record byte length |

**Index:** `ix_marc_record_index_sector` (base, sector_id)

---

## settings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| scope | Enum(SettingsScope) | PK | Configuration scope |
| data | JSONB | NOT NULL | Scope-specific settings |
| created_at | TIMESTAMP(tz) | default now | |
| updated_at | TIMESTAMP(tz) | auto-updated | |

**Scopes:** Catalog, Tasks, Validation, AuthorityLinking, Comparison, ProcessRecords, Maintenance

---

## catalog_records_analytics (Materialized View)

Denormalized view for DuckDB-accelerated faceting (`pg_duckdb` extension). Refreshed concurrently after data-changing tasks.

| Column | Source | Description |
|--------|--------|-------------|
| id | catalog_records.id | PK |
| base | catalog_records.base | |
| system_number | catalog_records.system_number | |
| type_of_record | catalog_records.type_of_record | |
| bibliographic_level | catalog_records.bibliographic_level | |
| is_deleted | catalog_records.deleted | |
| is_processed | processed_at IS NOT NULL | |
| authority_link_linkers | array_agg(DISTINCT al.linker) | |
| authority_link_bases | array_agg(DISTINCT al.base) | |
| comparison_bases | array_agg(DISTINCT cmp.base) | |
| match_qualities | array_agg(DISTINCT CASE score→Excellent/Moderate/Poor) | |
| overall_scores | array_agg(score) | All comparison scores |
| field_explanations | array_agg(DISTINCT explanation from field_results) | Nested JSONB extraction |
| validators | array_agg(DISTINCT v.validator) | |
| validation_statuses | array_agg(DISTINCT v.result→status) | |
| validation_target_tags | array_agg(DISTINCT v.result→target→tag) | |
| validation_reasons | array_agg(DISTINCT v.result→reason) | |
| reviewed_aspects | array_agg(DISTINCT rr.aspect_name) | Current reviews only |
| review_status | CASE→ReviewNotNeeded/Reviewed/PartiallyReviewed/Unreviewed | Computed from reviews vs aspects |
| latest_sync, latest_transaction, processed_at, updated_at | catalog_records.* | |

**Joins:** LEFT JOIN authority_links, comparisons, validations, record_reviews (WHERE status='current')  
**Filter:** WHERE source_type = 'Main'  
**Unique index:** `idx_analytics_id` (enables CONCURRENTLY refresh)

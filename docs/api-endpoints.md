# API Endpoints

## Authentication (`/auth`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/auth/sign-up` | Public | Register new user (assigned Guest role) |
| POST | `/auth/login` | Public | Login, sets httponly access_token + refresh_token cookies |
| POST | `/auth/refresh` | Cookie | Refresh access token using refresh_token cookie |
| POST | `/auth/logout` | Authenticated | Clear auth cookies |
| GET | `/auth/me` | Authenticated | Get current user profile + permissions |

### OIDC (`/auth/oidc`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/auth/oidc/login` | Public | Redirect to Keycloak authorization |
| GET | `/auth/oidc/callback` | Public | Handle Keycloak callback, provision user, set cookies |
| GET | `/auth/oidc/enabled` | Public | Check if OIDC is enabled + default flag |

**Token details:**
- Access token: HS256 JWT, 15min expiry, httponly cookie `access_token`
- Refresh token: HS256 JWT, 7d expiry, httponly cookie `refresh_token` (path: `/api/auth`)

---

## Catalog Records (`/catalog-records`)

### Search & Facets

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/catalog-records/search` | ReadRecords | Search records with filters, pagination, sorting |
| POST | `/catalog-records/facets` | ReadRecords | Get facet counts (runs on DuckDB materialized view) |
| POST | `/catalog-records/facets-preview` | ReadRecords | Get per-value facet previews for hover effect |

**Search request body:**
```json
{
  "filters": { /* RecordFilter */ },
  "page": 1,
  "page_size": 25,
  "sort_by": "latest_sync",
  "sort_order": "desc"
}
```

**RecordFilter fields:**
- `record_ids`, `text_query`, `bases`, `type_of_record`, `bibliographic_level`
- `deleted`, `processed` (boolean)
- `review_statuses`, `authority_link_linkers`, `authority_link_bases`
- `comparison_bases`, `match_qualities`, `field_explanations`
- `validators`, `validation_statuses`, `validation_target_tags`, `validation_reasons`
- `score_min`, `score_max`

**Facets request body:**
```json
{
  "filters": { /* RecordFilter */ }
}
```

**Facets preview request body:**
```json
{
  "filters": { /* RecordFilter */ },
  "target_field": "validators"
}
```

### Record Details

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/catalog-records/{base}/{sys_num}/marc` | ReadRecords | Get parsed MARC record |
| GET | `/catalog-records/{base}/{sys_num}/comparisons` | ReadRecords | Get all comparisons for record |
| GET | `/catalog-records/{base}/{sys_num}/validations` | ReadRecords | Get all validations for record |
| GET | `/catalog-records/{base}/{sys_num}/reviews` | ReadRecords | Get current + historical reviews |

### Reviews

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/catalog-records/{base}/{sys_num}/review` | ReviewRecords | Create review for aspect |
| DELETE | `/catalog-records/{base}/{sys_num}/review?aspect_name=X` | ReviewRecords | Delete review (ManageReviews if not own) |

### Record Import (all return `TaskSchema`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/catalog-records/fetch` | AddRecords | Fetch single record from Aleph OAI |
| POST | `/catalog-records/fetch-batch` | AddRecords | Batch fetch records |
| POST | `/catalog-records/sync` | SyncRecordsFromCatalog | Full sync from catalog by base (locked per base) |
| POST | `/catalog-records/process` | ProcessRecords | Run full pipeline (link + compare + validate) |

---

## Record Processing Tasks (all return `TaskSchema`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/comparison/task` | RunPartialRecordTasks | Run comparison on filtered records |
| POST | `/authority-linking/task` | RunPartialRecordTasks | Run authority linking on filtered records |
| POST | `/validation/task` | RunPartialRecordTasks | Run validation on filtered records |

---

## Tasks (`/tasks`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/tasks/search-own` | ManageTasks | Search own tasks (paginated, filterable by status) |
| POST | `/tasks/search-all` | ManageAllTasks | Search all users' tasks |
| GET | `/tasks/{task_id}/traceback` | ManageTasks | Get task log lines |
| PATCH | `/tasks/{task_id}/revoke` | ManageTasks | Revoke a running task |
| POST | `/tasks/delete` | ManageAllTasks | Delete completed/failed/revoked tasks |

---

## Settings (`/settings`)

### System Settings (Permission: `ManageAppSettings`)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/settings/system/catalog` | Aleph OAI client configs |
| GET/POST | `/settings/system/tasks` | Task execution parameters |
| GET/POST | `/settings/system/maintenance` | Periodic task schedules (syncs redbeat) |

### Record Tool Settings (Permission: `ManageTaskSettings`)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/settings/record-tools/authority-linkers` | Authority linker configs |
| GET/POST | `/settings/record-tools/comparators` | Comparator configs |
| GET/POST | `/settings/record-tools/validators` | Validator configs |
| GET/POST | `/settings/record-tools/process-records` | Process pipeline config (target bases, tools) |

---

## Access Control (`/access-control`)

All require `ManageAccessControl` permission.

### Roles

| Method | Path | Description |
|--------|------|-------------|
| GET | `/access-control/roles` | List roles (paginated) |
| POST | `/access-control/roles` | Create role |
| PUT | `/access-control/roles/{role_id}` | Update role |
| DELETE | `/access-control/roles/{role_id}` | Delete role |

### Users

| Method | Path | Description |
|--------|------|-------------|
| GET | `/access-control/users` | List users (paginated, filter by email) |
| PATCH | `/access-control/users/{user_id}/assign-role/{role_id}` | Assign role to user |
| PATCH | `/access-control/users/{user_id}/unassign-role/{role_id}` | Remove role from user |

---

## Maintenance (`/maintenance`)

All require `ManageAppSettings` permission. All return `TaskSchema`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/maintenance/refresh-analytics` | Refresh `catalog_records_analytics` materialized view |
| POST | `/maintenance/cleanup-stale-locks` | Remove stale Redis distributed locks |
| POST | `/maintenance/compact-sectors` | Recompact MARC sector storage |
| POST | `/maintenance/rebuild-search-vectors` | Rebuild search_text and tsvector for all records |
| POST | `/maintenance/delete-tasks` | Delete old completed/failed/revoked tasks |

---

## System (`/system`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/system/health` | Public | Health check (DB + Redis), returns 200 or 503 |
| GET | `/system/info` | Authenticated | System info (version, commit, uptime, bases, validators) |
| GET | `/system/locks` | Authenticated | List active distributed lock names |

---

## WebSocket (`/ws`)

- **Protocol:** WebSocket
- **Auth:** `access_token` cookie
- **Events sent to client:**

| Event Type | Fields | Sent To |
|------------|--------|---------|
| `task_status` | task_id, task_type, name, status, severity, created_by | Task creator + ManageAllTasks users |
| `task_progress` | task_id, progress (0.0-1.0), created_by | Task creator + ManageAllTasks users |
| `lock_acquired` | lock_name | All connected users |
| `lock_released` | lock_name | All connected users |

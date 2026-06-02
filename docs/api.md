# API Endpoints

## **Permissions**

| Permission               | Description                                          |
| ------------------------ | ---------------------------------------------------- |
| `ReadRecords`            | View catalog records and search results              |
| `AddRecords`             | Add new records to the catalog                       |
| `SyncRecordsFromCatalog` | Synchronize records from the catalog                 |
| `ReviewRecords`          | Create and manage own reviews on records             |
| `ManageReviews`          | Manage all reviews (including other users' reviews)  |
| `ProcessRecords`         | Run the full processing pipeline on records          |
| `RunPartialRecordTasks`  | Run individual tasks (validation, comparison, etc.)  |
| `ManageTasks`            | View and manage own tasks                            |
| `ManageAllTasks`         | View and manage all tasks in the system              |
| `ManageAccessControl`    | Configure user roles and permissions                 |
| `ManageAppSettings`      | Update global application and maintenance settings   |
| `ManageTaskSettings`     | Configure record tools (validators, linkers, etc.)   |

### Permission Dependencies

Granting a permission automatically includes its dependencies:

- `AddRecords` → `ReadRecords`
- `SyncRecordsFromCatalog` → `ReadRecords`, `AddRecords`, `ManageTasks`
- `ReviewRecords` → `ReadRecords`
- `ManageReviews` → `ReviewRecords`
- `ProcessRecords` → `ReadRecords`
- `RunPartialRecordTasks` → `ReadRecords`
- `ManageTasks` → `ProcessRecords`, `RunPartialRecordTasks`
- `ManageAllTasks` → `ManageTasks`
- `ManageTaskSettings` → `ManageTasks`

---

## **Authentication**

The application uses **httpOnly cookie-based authentication**. On successful login, the server sets `access_token` and `refresh_token` cookies. All subsequent requests are authenticated via these cookies.

### `POST /auth/sign-up`

**Description:** Register a new user.

**Request Body:**

```json
{
  "email": "user@example.com",
  "first_name": "string",
  "last_name": "string",
  "password": "string (min 8 characters)"
}
```

**Successful Response:** `201 Created`

---

### `POST /auth/login`

**Description:** Login and receive authentication cookies.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

**Successful Response:**

```json
{
  "status": "ok"
}
```

Sets `access_token` and `refresh_token` httpOnly cookies.

---

### `POST /auth/refresh`

**Description:** Refresh the access token using the refresh token cookie.

**Successful Response:**

```json
{
  "status": "ok"
}
```

Sets new `access_token` and `refresh_token` cookies.

---

### `POST /auth/logout`

**Description:** Clear authentication cookies.

**Successful Response:**

```json
{
  "status": "ok"
}
```

---

### `GET /auth/me`

**Description:** Retrieve current user details.

**Successful Response:**

```json
{
  "id": "uuid",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "roles": [
    {
      "id": 0,
      "name": "string"
    }
  ],
  "permissions": ["ReadRecords"]
}
```

---

### OIDC Authentication (Optional)

When configured, the application supports OpenID Connect (Keycloak) authentication.

#### `GET /auth/oidc/enabled`

**Description:** Check if OIDC authentication is enabled.

**Response:** `{"enabled": bool, "default": bool}`

#### `GET /auth/oidc/login`

**Description:** Redirect to Keycloak authorization page. Query parameter: `redirect` (default `/`).

#### `GET /auth/oidc/callback`

**Description:** Handle Keycloak callback. Sets auth cookies and redirects to the original page.

---

## **Roles and Permissions Management**

**Required Permission:** `ManageAccessControl`

---

### `GET /access-control/roles`

**Description:** List all roles with their permissions.

**Request Parameters (optional):**

* `page` (integer, default 1)
* `page_size` (integer, default 20)

**Successful Response:**

```json
{
  "items": [
    {
      "id": 0,
      "name": "string",
      "permissions": ["ReadRecords"],
      "immutable": true,
      "protected": true
    }
  ],
  "num_found": 0
}
```

---

### `POST /access-control/roles`

**Description:** Create a new role with specific permissions.

**Request Body:**

```json
{
  "name": "catalog_admin",
  "permissions": ["ReadRecords", "AddRecords"]
}
```

**Successful Response:**

```json
{
  "id": 0,
  "name": "catalog_admin",
  "permissions": ["ReadRecords", "AddRecords"],
  "immutable": false,
  "protected": false
}
```

---

### `PUT /access-control/roles/{role_id}`

**Description:** Update an existing role.

**Request Body:**

```json
{
  "name": "string",
  "permissions": ["ReadRecords", "AddRecords"]
}
```

**Successful Response:** Updated `RoleSchema`

---

### `DELETE /access-control/roles/{role_id}`

**Description:** Delete a role.

**Successful Response:** Deleted `RoleSchema`

---

### `GET /access-control/users`

**Description:** List users with their roles.

**Request Parameters (optional):**

* `page` (integer, default 1)
* `page_size` (integer, default 20)
* `email` (string, filter by email)

**Successful Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "email": "string",
      "first_name": "string",
      "last_name": "string",
      "roles": [
        {
          "id": 0,
          "name": "string"
        }
      ]
    }
  ],
  "num_found": 0
}
```

---

### `PATCH /access-control/users/{user_id}/assign-role/{role_id}`

**Description:** Assign a role to a user.

**Successful Response:** `200 OK` with updated `UserSchema`

---

### `PATCH /access-control/users/{user_id}/unassign-role/{role_id}`

**Description:** Unassign a role from a user.

**Successful Response:** `200 OK` with updated `UserSchema`

---

## **Catalog Records**

---

### `POST /catalog-records/search`

**Description:** Search catalog records using structured filters.
**Permission Required:** `ReadRecords`

**Request Body:**

```json
{
  "filters": {
    "bases": ["MZK01"],
    "text_query": "string",
    "type_of_record": ["a"],
    "bibliographic_level": ["m"],
    "deleted": false,
    "processed": true,
    "review_statuses": ["reviewed"],
    "match_qualities": ["Excellent", "Moderate"],
    "score_min": 0.5,
    "score_max": 1.0,
    "validators": ["kramerius-links"],
    "validation_statuses": ["Valid", "Invalid"],
    "authority_link_linkers": ["knihovny-cz"],
    "authority_link_bases": ["SKC"],
    "comparison_bases": ["SKC"]
  },
  "page": 1,
  "page_size": 25,
  "sort_by": "id",
  "sort_order": "asc"
}
```

All filter fields are optional. Available `sort_by` values: `id`, `base`, `system_number`, `latest_sync`, `updated_at`, `comparison_score`.

**Response:**

```json
{
  "items": [
    {
      "id": "MZK01/001818019",
      "base": "MZK01",
      "system_number": "001818019",
      "title": "string",
      "authors": ["string"],
      "type_of_record": "a",
      "bibliographic_level": "m",
      "state": ["string"],
      "authority_links": [
        {"linker": "knihovny-cz", "base": "SKC", "authority_record_id": "SKC/000123456"}
      ],
      "comparisons": [
        {"comparator": "default", "base": "SKC", "other_record_id": "SKC/000123456", "overall_score": 0.95, "match_quality": "Excellent"}
      ],
      "validations": [
        {"validator": "kramerius-links", "target_tag": "856", "status": "Valid"}
      ],
      "latest_sync": "2025-10-31T12:00:00Z",
      "latest_transaction": "2025-10-31T12:00:00Z",
      "processed_at": "2025-10-31T12:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 25
}
```

---

### `POST /catalog-records/facets`

**Description:** Get aggregated facets for catalog records matching filters.
**Permission Required:** `ReadRecords`

**Request Body:**

```json
{
  "filters": { /* RecordFilter */ }
}
```

**Response:**

```json
{
  "facets": [
    {"field": "base", "buckets": [{"key": "MZK01", "count": 50}]}
  ],
  "histograms": [
    {"field": "comparison_score", "buckets": [{"min": 0.0, "max": 0.5, "count": 10}]}
  ],
  "total": 100
}
```

---

### `POST /catalog-records/facets-preview`

**Description:** Preview facet distributions grouped by values of a target field.
**Permission Required:** `ReadRecords`

**Request Body:**

```json
{
  "filters": { /* RecordFilter */ },
  "target_field": "base"
}
```

---

### `GET /catalog-records/{base}/{system_number}/marc`

**Description:** Return the MARC record in JSON format.
**Permission Required:** `ReadRecords`

**Response:** MARC record in JSON format (marcdantic structure).

---

### `GET /catalog-records/{base}/{system_number}/comparisons`

**Description:** Get comparison results for a record.
**Permission Required:** `ReadRecords`

---

### `GET /catalog-records/{base}/{system_number}/validations`

**Description:** Get validation results for a record.
**Permission Required:** `ReadRecords`

---

### `POST /catalog-records/fetch`

**Description:** Fetch a single MARC record by system number from the configured catalog.
**Permission Required:** `AddRecords`

**Request Body:**

```json
{
  "base": "MZK01",
  "system_number": "001818019"
}
```

**Response:** `TaskSchema`

---

### `POST /catalog-records/fetch-batch`

**Description:** Fetch multiple MARC records in batch by system numbers.
**Permission Required:** `AddRecords`

**Request Body:**

```json
{
  "per_base": [
    {
      "base": "MZK01",
      "system_numbers": ["001818019", "001618553", "001778730"]
    }
  ]
}
```

**Response:** `TaskSchema`

---

### `POST /catalog-records/sync`

**Description:** Synchronize MARC records from the catalog. Fetches changes from `from_date` onwards.
**Permission Required:** `SyncRecordsFromCatalog`

**Request Body:**

```json
{
  "base": "MZK01",
  "from_date": "2025-10-01"
}
```

Both fields are required. `from_date` can be `null` to sync all records.

**Response:** `TaskSchema`

---

### `POST /catalog-records/process`

**Description:** Run the full processing pipeline (authority linking, comparison, validation) on records matching filters.
**Permission Required:** `ProcessRecords`

**Request Body:**

```json
{
  "bases": ["MZK01"],
  "text_query": "string"
}
```

The request body is a `RecordFilter` (same fields as the search filters).

**Response:** `TaskSchema`

---

### Reviews

#### `GET /catalog-records/{base}/{system_number}/reviews`

**Description:** Get current and historical reviews for a record.
**Permission Required:** `ReadRecords`

**Response:**

```json
{
  "current": [
    {
      "id": "string",
      "record_id": "string",
      "aspect_name": "string",
      "note": "string",
      "reviewed_by": "uuid",
      "reviewer_name": "string",
      "reviewed_at": "2025-10-31T12:00:00Z",
      "status": "string"
    }
  ],
  "history": []
}
```

#### `POST /catalog-records/{base}/{system_number}/review`

**Description:** Create a review for a record.
**Permission Required:** `ReviewRecords`

**Request Body:**

```json
{
  "aspect_name": "string",
  "note": "optional string"
}
```

#### `DELETE /catalog-records/{base}/{system_number}/review`

**Description:** Delete a review. Users can delete their own reviews with `ReviewRecords`; deleting others' reviews requires `ManageReviews`.
**Permission Required:** `ReviewRecords` (own) or `ManageReviews` (others')

**Query Parameter:** `aspect_name` (string, required)

---

## **Validation**

### `POST /validation/task`

**Description:** Start a validation task for catalog records matching filters.
**Permission Required:** `RunPartialRecordTasks`

**Request Body:**

```json
{
  "validators": ["kramerius-links"],
  "filters": {
    "bases": ["MZK01"]
  }
}
```

**Response:** `TaskSchema`

---

## **Authority Linking**

### `POST /authority-linking/task`

**Description:** Start a task to link catalog records with authority records.
**Permission Required:** `RunPartialRecordTasks`

**Request Body:**

```json
{
  "linkers": ["knihovny-cz"],
  "target_base": "SKC",
  "filters": {
    "bases": ["MZK01"]
  }
}
```

**Response:** `TaskSchema`

---

## **Comparison**

### `POST /comparison/task`

**Description:** Start a task to compare catalog records with their linked authority records.
**Permission Required:** `RunPartialRecordTasks`

**Request Body:**

```json
{
  "target_base": "SKC",
  "filters": {
    "bases": ["MZK01"]
  }
}
```

**Response:** `TaskSchema`

---

## **Tasks**

The `TaskSchema` represents tasks in the system:

```json
{
  "task_id": "uuid",
  "name": "string",
  "type": "FetchRecord | FetchBatchOfRecords | SyncRecords | ValidateRecords | LinkRecordsToAuthorities | CompareRecords | ProcessRecords | DeleteTasks | RefreshAnalytics | CleanupStaleLocks | CompactSectors | RebuildSearchVectors",
  "status": "Pending | Started | Success | Failure | Revoked",
  "severity": "Info | Warning | Error | Critical",
  "created_by": "uuid",
  "created_at": "2025-10-31T12:00:00Z",
  "started_at": "2025-10-31T12:01:00Z",
  "finished_at": "2025-10-31T12:05:00Z",
  "progress": 0.75,
  "traceback_lines": 0
}
```

---

### `POST /tasks/search-own`

**Description:** Search your own tasks.
**Permission Required:** `ManageTasks`

**Request Body:**

```json
{
  "filters": {
    "type": ["FetchRecord", "SyncRecords"],
    "status": ["Pending", "Started"],
    "severity": ["Info", "Warning"]
  },
  "page": 1,
  "page_size": 25,
  "sort_by": "created_at",
  "sort_order": "desc"
}
```

All filter fields are optional. Available `sort_by` values: `created_at`, `started_at`, `finished_at`.

**Response:**

```json
{
  "items": [/* TaskSchema objects */],
  "total": 10,
  "page": 1,
  "page_size": 25
}
```

---

### `POST /tasks/search-all`

**Description:** Search all tasks in the system.
**Permission Required:** `ManageAllTasks`

**Request Body:** Same as `/tasks/search-own`.

**Response:** Same format as `/tasks/search-own`.

---

### `GET /tasks/{task_id}/traceback`

**Description:** Retrieve task traceback lines.
**Permission Required:** `ManageTasks` (own tasks) or `ManageAllTasks` (all tasks)

**Query Parameters:**

* `from` (integer, optional) — starting line number
* `to` (integer, optional) — ending line number

**Response:** Plain text of traceback lines.

---

### `PATCH /tasks/{task_id}/revoke`

**Description:** Revoke a pending or running task.
**Permission Required:** `ManageTasks` (own tasks) or `ManageAllTasks` (all tasks)

**Response:** `200 OK` with updated `TaskSchema`

---

### `POST /tasks/delete`

**Description:** Delete old tasks.
**Permission Required:** `ManageAllTasks`

**Request Body:**

```json
{
  "max_age_days": 30
}
```

`max_age_days` is optional — if omitted, deletes all finished tasks.

**Response:** `TaskSchema` (the delete task itself)

---

## **System Settings**

**Permission Required:** `ManageAppSettings`

### `GET /settings/system/{scope}`

**Description:** Retrieve application settings for the specified scope.

**Available scopes:** `catalog`, `tasks`, `maintenance`

**Response:** JSON object with settings for the specified scope.

---

### `POST /settings/system/{scope}`

**Description:** Update application settings for the specified scope.

**Available scopes:** `catalog`, `tasks`, `maintenance`

**Request Body:** JSON object with settings for the specified scope.

**Response:** Updated settings.

---

## **Record Tools Settings**

**Permission Required:** `ManageTaskSettings`

### `GET /settings/record-tools/{scope}`

**Description:** Retrieve record tools configuration for the specified scope.

**Available scopes:** `validators`, `authority-linkers`, `comparators`, `process-records`

**Response:** JSON object with configuration for the specified scope.

---

### `POST /settings/record-tools/{scope}`

**Description:** Update record tools configuration for the specified scope.

**Available scopes:** `validators`, `authority-linkers`, `comparators`, `process-records`

**Request Body:** JSON object with configuration for the specified scope.

**Response:** Updated configuration.

---

## **Maintenance**

**Permission Required:** `ManageAppSettings`

### `POST /maintenance/refresh-analytics`

**Description:** Refresh analytics data (aggregated counts, facets).

**Response:** `TaskSchema`

---

### `POST /maintenance/cleanup-stale-locks`

**Description:** Remove stale record locks.

**Response:** `TaskSchema`

---

### `POST /maintenance/compact-sectors`

**Description:** Compact database sectors.

**Response:** `TaskSchema`

---

### `POST /maintenance/rebuild-search-vectors`

**Description:** Rebuild full-text search vectors for all records.

**Response:** `TaskSchema`

---

### `POST /maintenance/delete-tasks`

**Description:** Delete old finished tasks.

**Query Parameter:** `max_age_days` (integer, optional)

**Response:** `TaskSchema`

---

## **System**

### `GET /system/health`

**Description:** Health check endpoint. Returns 200 if healthy, 503 if unhealthy.

**Response:**

```json
{
  "status": "healthy",
  "details": {
    "database": "ok"
  }
}
```

---

### `GET /system/info`

**Description:** Get system information. Requires authentication.

**Response:**

```json
{
  "system_version": "string",
  "system_commit": "string",
  "uptime_seconds": 0,
  "configured_bases": ["MZK01"],
  "authority_bases": ["SKC"],
  "enabled_authority_linkers": [
    {
      "name": "knihovny-cz",
      "target_bases": ["SKC"]
    }
  ],
  "enabled_validators": ["kramerius-links"],
  "kramerius_client_urls": {}
}
```

---

### `GET /system/locks`

**Description:** Get currently active record locks. Requires authentication.

**Response:** `["MZK01/001818019", ...]`

---

## **WebSocket**

### `WS /ws`

**Description:** WebSocket endpoint for real-time updates (task progress, status changes). Authenticated via the `access_token` cookie. Closes with code `4001` if the token is missing or invalid.

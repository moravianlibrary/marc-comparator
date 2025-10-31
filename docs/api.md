# API Endpoints

## **Permissions**

| Permission               | Description                             |
| ------------------------ | --------------------------------------- |
| `ReadRecords`            | View catalog records and search results |
| `AddRecords`             | Add new records to the catalog          |
| `SyncRecordsFromCatalog` | Synchronize records from the catalog    |
| `RunRecordTasks`         | Execute automated tasks on records      |
| `ManageTasks`            | Read and manage own tasks               |
| `ManageAllTasks`         | Read and manage all tasks               |
| `ManageAccessControl`    | Configure user roles and permissions    |
| `ManageAppSettings`      | Update global application settings      |
| `ManageTaskSettings`     | Configure settings for individual tasks |
| `ManageSystem`           | Manage system resources                 |

---

## **Authentication**

### `POST /auth/`

**Description:** Register a new user.

**Request Body:**

```json
{
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "password": "string"
}
```

**Successful Response:** `201 Created`

```json
{
  "id": "uuid",
  "email": "string",
  "first_name": "string",
  "last_name": "string"
}
```

---

### `POST /auth/token`

**Description:** Obtain an access token.

**Request Form:**

* `username` (string)
* `password` (string)

**Successful Response:**

```json
{
  "access_token": "string",
  "token_type": "bearer"
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
      "name": "string",
      "permissions": ["ReadRecords"],
      "immutable": true,
      "protected": true
    }
  ],
  "permissions": ["ReadRecords"]
}
```

---

## **Roles and Permissions Management**

**Required Permission:** `ManageAccessControl`

---

### `GET /access-control/roles`

**Description:** List all roles with their permissions.

**Request Parameters (optional):**

* `page` (integer)
* `page_size` (integer)

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

### `PUT /access-control/roles/{id}`

**Description:** Update an existing role.

**Request Body:**

```json
{
  "name": "string",
  "permissions": ["ReadRecords", "AddRecords"]
}
```

**Successful Response:**

```json
{
  "id": 0,
  "name": "string",
  "permissions": ["ReadRecords", "AddRecords"],
  "immutable": false,
  "protected": false
}
```

---

### `DELETE /access-control/roles/{id}`

**Description:** Delete a role.

**Successful Response:**

```json
{
  "id": 0,
  "name": "string",
  "permissions": ["ReadRecords"],
  "immutable": false,
  "protected": false
}
```

---

### `GET /access-control/users`

**Description:** List users with their roles.

**Request Parameters (optional):**

* `page` (integer)
* `page_size` (integer)
* `email` (string, filter by email)

**Successful Response:** JSON schema

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
          "name": "string",
          "permissions": ["ReadRecords"],
          "immutable": false,
          "protected": false
        }
      ],
      "permissions": ["ReadRecords"]
    }
  ],
  "num_found": 0
}
```

---

### `PATCH /access-control/users/{user_id}/assign-role/{role_id}`

**Description:** Assign a role to a user.

**Required Permission:** `ManageAccessControl`

**Successful Response:** `200 OK`

```json
{
  "id": "uuid",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "roles": [
    {
      "id": 0,
      "name": "string",
      "permissions": ["ReadRecords"],
      "immutable": false,
      "protected": false
    }
  ],
  "permissions": ["ReadRecords"]
}
```

---

### `PATCH /access-control/users/{user_id}/assign-role{role_id}`

**Description:** Assign roles to a user.
**Permissions Required:** `Admin`
**Response:** `200 OK`
response returns user

---

## **Catalog Records**

---

### `POST /catalog-records/search`

**Description:** Search catalog records using a custom query.
**Permissions Required:** `ReadRecords`

**Request Body (Elasticsearch DSL query):**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** Raw Elasticsearch response.

---

### `POST /catalog-records/fetch`

**Description:** Fetch a single MARC record by system number.
**Permissions Required:** `AddRecords`

**Request Body:**

```json
{
  "base": "TEST",
  "system_number": "123"
}
```

**Response:** `TaskSchema`

---

### `POST /catalog-records/fetch-batch`

**Description:** Fetch multiple MARC records in batch by system numbers.
**Permissions Required:** `AddRecords`

**Request Body (example JSON based on `FetchBatchOfRecordsData`):**

```json
{
  "per_base": [
    {
      "base": "TEST",
      "system_numbers": ["123", "124", "125"]
    },
    {
      "base": "MAIN",
      "system_numbers": ["456", "457"]
    }
  ]
}
```

**Response:** `TaskSchema`

---

### `POST /catalog-records/sync`

**Description:** Synchronize MARC records from the Aleph catalog. Only changes from `from_date` to `to_date` are fetched.
**Permissions Required:** `SyncRecordsFromCatalog`

**Request Body:**

```json
{
  "base": "TEST",
  "from_date": "2025-10-01T00:00:00Z",  // optional
  "to_date": "2025-10-01T00:00:00Z",  // optional
}
```

**Response:** `TaskSchema`

---

### `POST /catalog-records/hide`

**Description:** Hide catalog records matching a query.
**Permissions Required:** `RunRecordTasks`

**Request Parameters:**

* `reason`: Explanation for hiding records (optional)

**Request Body:** 

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** `TaskSchema`

---

### `POST /catalog-records/reindex`

**Description:** Reindex catalog records matching a query.
**Permissions Required:** `RunRecordTasks`

**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** `TaskSchema`

---

## **Validation**

### `POST /validation/task`

**Description:** Start a validation task for catalog records that match a query, using the specified validators.
**Permissions Required:** `RunRecordTasks`

**Request Body:**

```json
{
  "validators": [
    "kramerius-links"
  ],
  "query": {
    /* Elasticsearch DSL query */
  }
}
```

**Response:** `TaskSchema`

---

## **Authority Linking**

### `POST /authority-linking/task`

**Description:** Start a task to link catalog records with authority records from the specified authority base.
**Permissions Required:** `RunRecordTasks`

**Request Body:**

```json
{
  "linkers": [
    "knihovny-cz"
  ],
  "target_base": "string",
  "query": {
    /* Elasticsearch DSL query */
  }
}
```

**Response:** `TaskSchema`

---

## **Comparison**

### `POST /comparison/task`

**Description:** Start a task to compare catalog records with linked authority records from the specified base.
**Permissions Required:** `RunRecordTasks`

**Request Body:**

```json
{
  "comparator": "rule-based",
  "target_base": "string",
  "query": {
    /* Elasticsearch DSL query */
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
  "type": "FetchRecord | FetchBatchOfRecords | SyncRecords | ValidateRecords | LinkRecordsToAuthorities | CompareRecords | ReindexRecords | DeleteTasks",
  "status": "Pending | Started | Success | Failure | Revoked",
  "traceback_lines": 0,
  "created_by": "uuid",
  "created_at": "2025-10-31T12:00:00Z",
  "started_at": "2025-10-31T12:01:00Z",
  "finished_at": "2025-10-31T12:05:00Z"
}
```

---

### `POST /tasks/search-own`

**Description:** Search your own tasks using index queries.
**Permissions Required:** `ManageTasks`

**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** Raw Elasticsearch response.

---

### `POST /tasks/search-all`

**Description:** Search all tasks in the system.
**Permissions Required:** `ManageAllTasks`

**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** Raw Elasticsearch response.

---

### `GET /tasks/{task_id}/traceback`

**Description:** Retrieve task traceback lines.
**Permissions Required:** User must have the same permission as the task owner (`ManageTasks`) or global (`ManageAllTasks`)

**Request Parameters:**

* `from` (integer, optional) — starting line number
* `to` (integer, optional) — ending line number

**Response:** Plain text of traceback lines

---

### `PATCH /tasks/{task_id}/kill`

**Description:** Kill a running task.
**Permissions Required:** User must have the same permission as the task owner (`ManageTasks`) or global (`ManageAllTasks`)

**Response:** `200 OK` with updated task info (`TaskSchema`)

---

### `POST /tasks/delete`

**Description:** Plan deletion of selected tasks based on query.
**Permissions Required:** User must have the same permission as the task owner (`ManageTasks`) or global (`ManageAllTasks`)

**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** Raw Elasticsearch response.

---

## **App Settings**

### `GET /settings/app/{scope}/schema`

**Description:** Retrieve the schema for application settings of the specified scope.
**Permissions Required:** `ManageAppSettings`

**Path Parameters:**

* `scope` (string, required) — Scope of the app settings
  *Available values:* `Catalog`, `Task`

**Response:** JSON schema describing the structure of the settings for the specified scope

---

### `GET /settings/app/{scope}`

**Description:** Retrieve the current application settings for the specified scope.
**Permissions Required:** `ManageAppSettings`

**Path Parameters:**

* `scope` (string, required) — Scope of the app settings
  *Available values:* `Catalog`, `Task`

**Response:** JSON object containing the current settings for the specified scope

---

### `POST /settings/app/{scope}`

**Description:** Update or set application settings for the specified scope.
**Permissions Required:** `ManageAppSettings`

**Path Parameters:**

* `scope` (string, required) — Scope of the app settings
  *Available values:* `Catalog`, `Task`

**Request Body:** JSON object containing settings for the specified scope, based on the schema

**Response:** JSON object of the updated settings for that scope

---

## **Task Settings**

### `GET /settings/tasks/{scope}/schema`

**Description:** Retrieve the schema for task settings of the specified scope.
**Permissions Required:** `ManageTaskSettings`

**Path Parameters:**

* `scope` (string, required) — Scope of the task settings
  *Available values:* `Validation`, `AuthorityLinking`, `Comparison`

**Response:** JSON schema describing the structure of the settings for the specified scope

---

### `GET /settings/tasks/{scope}`

**Description:** Retrieve the current task settings for the specified scope.
**Permissions Required:** `ManageTaskSettings`

**Path Parameters:**

* `scope` (string, required) — Scope of the task settings
  *Available values:* `Validation`, `AuthorityLinking`, `Comparison`

**Response:** JSON object containing the current settings for the specified scope

---

### `POST /settings/tasks/{scope}`

**Description:** Update or set task settings for the specified scope.
**Permissions Required:** `ManageTaskSettings`

**Path Parameters:**

* `scope` (string, required) — Scope of the task settings
  *Available values:* `Validation`, `AuthorityLinking`, `Comparison`

**Request Body:** JSON object containing settings for the specified scope, based on the schema

**Response:** JSON object of the updated settings for that scope

---

## **System**

### `POST /system/recreate-indexes`

**Description:** Start a task to recreate all indexes and reindex all entities.  
**Permissions Required:** `ManageSystem`

**Response:** `TaskSchema`

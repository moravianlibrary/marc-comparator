Here’s a revised version of your API endpoints spec with fixes, added missing details, consistent formatting, and clarified permission lists:

---

# API Endpoints

## **Permissions**

| Permission | Description                                    |
| ---------- | ---------------------------------------------- |
| Read       | View catalog records and search results        |
| Write      | Fetch and synchronize records                  |
| Hide       | Mark records as hidden                         |
| Validate   | Start validation tasks                         |
| Pair       | Pair catalog records with authority records    |
| Compare    | Compare catalog records with authority records |
| Admin      | Manage users, roles, and permissions           |

---

## **Auth**

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

**Response:** `201 Created`

---

### `POST /auth/token`

**Description:** Obtain access token.
**Request Form:**

* `email` (string)
* `password` (string)

**Response:**

```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

---

## **Roles and Permissions Management** *(Admin only)*

### `GET /auth/roles`

**Description:** List all roles and their permissions.
**Permissions Required:** `Admin`
**Response:** List of roles with associated permissions

---

### `POST /auth/roles`

**Description:** Create a new role with permissions.
**Permissions Required:** `Admin`
**Request Body:**

```json
{
  "name": "catalog_admin",
  "permissions": ["Read", "Write", "Validate"]
}
```

**Response:** `201 Created`

---

### `GET /auth/users`

**Description:** List all users with their roles.
**Permissions Required:** `Admin`
**Request Parameters:** `page`, `page_size`
**Response:** Paginated list of users

---

### `POST /auth/users/{user_id}/roles`

**Description:** Assign roles to a user.
**Permissions Required:** `Admin`
**Request Body:**

```json
{
  "roles": ["catalog_admin"]
}
```

**Response:** `200 OK`

---

## **Catalog**

### `POST /catalog/fetch`

**Description:** Fetch a single MARC record.
**Permissions Required:** `Write`
**Request Body:**

```json
{
  "base": "TEST",
  "system_number": "123"
}
```

**Response:** `TaskSchema`

---

### `POST /catalog/fetch-batch`

**Description:** Fetch multiple records from a file.
**Permissions Required:** `Write`
**Request Parameters:** `base` - optional, provided if the file contains only system numbers.
**Request Body:** Multipart file containing either `base-system_number` lines or just `system_number` lines (then the base is passed by parameter).
**Response:** `TaskSchema`

---

### `POST /catalog/sync`

**Description:** Synchronize MARC records from Aleph catalog, with changes starting from `from_date`.
**Permissions Required:** `Write`
**Request Body:**

```json
{
  "base": "TEST",
  "from_date": "Optional date"
}
```

**Response:** `TaskSchema`

---

## **Records**

### `POST /records/search`

**Description:** Search catalog records via Elasticsearch proxy.
**Permissions Required:** `Read`
**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** Elasticsearch response - unchanged.

---

### `POST /records/hide`

**Description:** Hide records matching a query.
**Permissions Required:** `Hide`
**Request Parameters:** `reason` - optional explanation
**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:**

```json
{
  "hidden_count": 10
}
```

---

## **Validation**

### `POST /validation`

**Description:** Start validation task for records matching a query.
**Permissions Required:** `Validate`
**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** `TaskSchema`

---

## **Authorities**

### `POST /authorities/pair`

**Description:** Pair catalog records with authority records from a selected base.
**Permissions Required:** `Pair`
**Request Parameters:** `authority_base`
**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** `TaskSchema`

---

## **Comparison**

### `POST /comparison`

**Description:** Compare catalog records with authority records from a selected base.
**Permissions Required:** `Compare`
**Request Parameters:** `authority_base`
**Request Body:**

```json
{
  /* Elasticsearch DSL query */
}
```

**Response:** `TaskSchema`

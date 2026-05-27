# Client Notifications & Task Tracking

## Architecture Overview

```
Backend Task → Redis Pub/Sub → WebSocket Server → WSClient → use-ws-events hook
                                                                    ↓
                                              ┌─────────────────────┼──────────────────┐
                                              ↓                     ↓                  ↓
                                      Sonner Toast          Toast History       Query Invalidation
                                    (transient popup)    (persistent sheet)    (refetch stale data)
```

---

## WebSocket Connection (`lib/ws-client.ts`)

Singleton `WSClient` class managing a persistent WebSocket connection.

**Connection:** `ws[s]://{host}/api/ws` — authenticated via `access_token` cookie.

**Reconnection:** Exponential backoff starting at 1s, max 30s, reconnects automatically on close/error.

**API:**
- `connect()` — establishes connection
- `disconnect()` — closes connection
- `on(type, handler)` — registers handler, returns unsubscribe function

---

## WebSocket Events (`hooks/use-ws-events.ts`)

Connects on mount, disconnects on unmount. Handles 4 event types:

### `task_status`

Fired when a task changes status (Started, Success, Failure, Revoked).

**Payload:** `{ task_id, task_type, name, status, severity, created_by }`

**Actions:**
- Invalidates `["tasks"]` queries (refreshes task list)
- Shows sonner toast:
  - `Started` → `toast.info(taskName)` — also saves to notification history
  - `Success` → `toast.success(taskName)` — also saves to notification history
  - `Failure` → `toast.error(taskName)` — also saves to notification history
- Task name is resolved via i18n: `t("tasks:type.{task_type}")`

### `task_progress`

Fired periodically while a task runs (controlled by `progress_update_interval` setting).

**Payload:** `{ task_id, progress, created_by }`

**Actions:**
- Invalidates `["tasks", "running"]` query — updates progress bars in main banner

### `lock_acquired`

Fired when a distributed lock is taken (e.g., catalog sync starting).

**Payload:** `{ lock_name }`

**Actions:**
- Invalidates `["system", "locks"]` query — shows/updates lock banner

### `lock_released`

Fired when a distributed lock is released.

**Payload:** `{ lock_name }`

**Actions:**
- Invalidates `["system", "locks"]` query — hides lock banner

---

## Toast System (Sonner)

Transient popup notifications using the `sonner` library.

**Toast types used:**
- `toast.info()` — task started
- `toast.success()` — task completed
- `toast.error()` — task failed, API errors
- `toast.warning()` — conflict (e.g., 409 sync already running)

**API Error Toasts** (`components/api-error-listener.tsx`):
- Listens to custom `"api-error"` window events dispatched by the API client interceptor
- Shows error toast with status code, URL, message — infinite duration, close button
- Copyable JSON details on click
- 409 responses are excluded (handled by callers)

---

## Notification History (`layout/toast-history.tsx`)

Persistent notification store using `useSyncExternalStore` pattern (external to React).

**Store:**
- In-memory array, max 100 entries
- Each entry: `{ id, title, description, variant, timestamp, read, taskId }`
- Deduplication: if `taskId` + `variant` already exists, skip (prevents duplicate notifications for instant tasks)

**API:**
- `addNotification(entry)` — adds to store, notifies subscribers
- `useNotificationStore()` — returns `{ notifications, unreadCount, markAllRead() }`

**UI:**
- Bell icon in main banner with unread count badge
- Sheet (slide-out drawer) showing all notifications
- Mark all as read on open
- Each notification shows: icon (by variant), title, description, relative timestamp
- `px-4` padding for proper spacing from sheet edges

---

## Task Progress Tracking (`layout/task-progress.tsx`)

Displays running task progress in the main banner header.

**Data source:** Polls `POST /tasks/search-own` with filter `{ status: ["Started"] }`, page_size 20.
- Only enabled when user has `ManageTasks` permission
- Conditional refetch: polls every 5s while any task has status "Started", stops when none running

**Display modes:**

**Single running task:**
- Inline progress bar with task name (translated via `t("tasks:type.{task.type}")`)
- Shows percentage

**Multiple running tasks:**
- Summary text: "N tasks running"
- Popover on click showing list of tasks with individual progress bars

**No running tasks:** Hidden (no UI rendered)

---

## Lock Banner (`layout/lock-banner.tsx`)

Yellow warning banner shown when system locks are active.

**Data source:** `GET /system/locks` — returns array of lock name strings.

**Display:** Lists active lock names (e.g., `catalog_sync_MZK01`) in a dismissible banner below the header.

**Integration with sync form:** The `sync-form.tsx` also queries locks to disable the submit button when a sync lock for the selected base exists.

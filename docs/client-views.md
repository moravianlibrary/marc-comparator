# Client Views

## Records Page (`records-page.tsx`)

Central hub with 4 tabs: **Plots**, **Table**, **Carousel**, **Addition**. All tabs share a unified filter state managed via URL search params (`nuqs`). The tab header shows active filter count (Plots), total results (Table), and current position (Carousel).

### Shared Filter State (`use-record-filters.ts`)

All record filters live in URL params, making them shareable, bookmarkable, and preserved across tabs.

| URL Param | Type | Description |
|-----------|------|-------------|
| `tab` | `plots\|table\|carousel\|addition` | Active tab |
| `page`, `pageSize` | int | Pagination |
| `sortBy`, `sortOrder` | string | Sort config |
| `search` | string | Full-text search query |
| `bases` | string[] | Filter by catalog base |
| `typeOfRecord` | string[] | MARC leader byte 6 |
| `bibliographicLevel` | string[] | MARC leader byte 7 |
| `reviewStatuses` | string[] | Reviewed, PartiallyReviewed, Unreviewed, ReviewNotNeeded |
| `deleted` | `"true"\|"false"\|""` | Deletion state |
| `processed` | `"true"\|"false"\|""` | Processing state |
| `authorityLinkLinkers` | string[] | Authority linker names |
| `authorityLinkBases` | string[] | Authority link target bases |
| `comparisonBases` | string[] | Comparison target bases |
| `matchQualities` | string[] | Excellent, Moderate, Poor |
| `fieldExplanations` | string[] | Comparison field explanations |
| `validators` | string[] | Validator names |
| `validationStatuses` | string[] | Valid, ForReview, Invalid, AdditionalInfo |
| `validationTargetTags` | string[] | Validated MARC field tags |
| `validationReasons` | string[] | Validation reason codes |
| `scoreMin`, `scoreMax` | float | Score range (0-1) |
| `recordId` | string | Direct record ID filter |
| `recordIndex` | int | Position within current page |
| `carouselView` | string | Active carousel sub-view |

Key functions: `buildRecordFilter()` constructs the API filter payload, `buildSearchPayload()` adds pagination/sorting, `toggleArrayFilter()` handles click-to-toggle, `clearFilters()` resets all.

---

### Plots Tab (`plots/plots-view.tsx`)

Interactive faceted visualization dashboard. Organized into 4 collapsible sections:

**1. Context Section** — Pill-based selectors for: base, authority link bases/linkers, comparison bases, validators. Each pill shows count; clicking toggles the filter.

**2. Records Section** — 3-column grid:
- **Record Status** (`StatusTripleFacet`): Three stacked horizontal bars for deleted/processed/review state
- **Type of Record** (`BarFacet`): Horizontal bar chart with interactive labels (labelWidth=240)
- **Bibliographic Level** (`DonutFacet`): Pie/donut chart

**3. Comparison Section** — 3-column grid:
- **Match Quality** (`RadialQuality`): Semicircle pie chart with center total, segments for Excellent/Moderate/Poor
- **Overall Score** (`HistogramFacet`): Score distribution histogram with range inputs
- **Field Explanations** (`BarFacet`): Horizontal bars with translated labels, show-more toggle at 10 items

**4. Validation Section** — Per-validator breakdowns:
- **Validation Status** (`RadialValidation`): Concentric radial bars for Valid/ForReview/Invalid/AdditionalInfo with legend
- **Validation Reasons** (`BarFacet`): Horizontal bars with translated labels

#### Hover Preview System

When hovering a facet value, the system shows how selecting that value would affect all other facets:
1. On mouse proximity to a chart, `usePrefetchFacetPreview()` fires a prefetch for that field
2. On hover, `usePreviewForValue()` picks the cached slice for the hovered value
3. Other charts render semi-transparent "shadow" bars/segments showing the projected distribution

The preview data is served by the `/catalog-records/facets-preview` endpoint which pre-computes facets for every value of the target field.

#### Section Visibility (`use-section-visibility.ts`)

Users can toggle which charts and sections are visible via `SectionConfig`. State is persisted in localStorage.

#### Data Flow

```
URL params → useRecordFilters() → buildRecordFilter()
                                      ↓
                            POST /catalog-records/facets
                                      ↓
                            useFacets() → facetsData
                                      ↓
                            facetsByField Map → chart components
```

---

### Table Tab (`table/table-view.tsx`)

Paginated data grid using TanStack Table (`@tanstack/react-table`).

**Features:**
- Full-text search with debounced input (300ms)
- Sortable columns (server-side): id, base, system_number, latest_sync, updated_at, comparison_score
- Configurable column visibility (persisted in localStorage via `ColumnConfig`)
- Page sizes: 10, 25, 50, 100, 1000
- Bulk actions: process records, run partial tasks (comparison, validation, authority linking)
- Click row → navigate to Carousel tab at that record index

**Columns** (`columns.tsx`):
- System Number, Title, Authors, Type of Record, Bibliographic Level
- State badges (Active/Deleted, Processed/Unprocessed, review status)
- Authority Links (count with linker/base breakdown popover)
- Comparisons (score badges per base with color coding)
- Validations (status badges per validator)
- Latest Sync, Latest Transaction

**Data Flow:**
```
URL params → buildSearchPayload() → POST /catalog-records/search → table rows
```

---

### Carousel Tab (`carousel/carousel-view.tsx`)

Record-by-record browser with navigation (prev/next) and detail views.

**Header** (`record-header.tsx`):
- Base, system number, title, authors
- State badges
- Navigation arrows (prev/next within filtered results, across pages)

**Sub-views** (switchable):
- **MARC Record** (`marc-table.tsx`): Full MARC display with leader, fixed fields, variable fields with subfield expansion
- **Comparison views**: One per comparison — shows field-by-field diff with scores, explanations, subfield details
- **Authority views**: One per authority link — shows linked authority record's MARC
- **Validation views**: One per validator — shows validation results with status, reason, details, hints

**Review System** (`review-button.tsx`, `use-reviews.ts`):
- Per-aspect review marking (each comparator/validator is an "aspect")
- Reviews can be created with optional notes
- Reviews become "outdated" when underlying data changes
- Reviews become "superseded" when a newer review is created

**Auto-selection**: When navigating records, the carousel auto-selects the matching authority/comparison view if one was previously active.

---

### Addition Tab (`addition/addition-view.tsx`)

Three forms for importing records into the system:

**1. Fetch Single** (`fetch-single-form.tsx`):
- Input: base (select), system number (text)
- Creates a FetchRecord task

**2. Fetch Batch** (`fetch-batch-form.tsx`):
- Input: list of {base, system_numbers}
- Creates a FetchBatchOfRecords task

**3. Sync from Catalog** (`sync-form.tsx`):
- Input: base (select)
- Creates a SyncRecords task
- Checks for active `catalog_sync_{base}` lock — disables submit if locked
- Handles 409 conflict response (sync already running)

---

## Tasks Page (`tasks/tasks-page.tsx`)

Split layout: task table (left) + task detail panel (right).

**Task Table** (`task-table.tsx`):
- Columns: Type (translated), Status (badge), Severity, Run Time, Created By (if ManageAllTasks), Actions
- Click row to select and show detail
- Revoke button for Started tasks
- "Created By" column resolves user UUIDs to names via `/access-control/users` query

**Task Detail** (`task-detail.tsx`):
- Shows task traceback/logs with live polling (2s interval while Started)
- Monospace log viewer

**Permissions:**
- `ManageTasks`: see own tasks, revoke own tasks
- `ManageAllTasks`: see all tasks, see created-by column, delete tasks

---

## Settings Page (`settings/settings-page.tsx`)

Scope-based settings editor with 7 scopes:

| Scope | Form Component | Key Settings |
|-------|---------------|--------------|
| Catalog | `catalog-settings-form.tsx` | Aleph OAI client configs (URL, base, set, prefix, metadataPrefix) |
| Tasks | `task-settings-form.tsx` | Progress update interval, indexing batch size |
| Authority Linkers | `authority-linking-settings-form.tsx` | KnihovnyCZ linker config (URL, target fields) |
| Comparators | `comparison-settings-form.tsx` | Comparator selection and config |
| Validators | `validation-settings-form.tsx` | Kramerius links validator config (URL patterns) |
| Process Records | `process-records-settings-form.tsx` | Target bases, authority linkers, validators to run |
| Maintenance | `maintenance-settings-form.tsx` | Periodic task cleanup, sector compaction schedules |

**UX:** Select scope → load current settings → edit form → Save/Discard with unsaved warning.

**Permissions:** `ManageAppSettings` for system settings (Catalog, Tasks, Maintenance), `ManageTaskSettings` for record tool settings.

---

## Access Control Page (`access-control/access-control-page.tsx`)

Two sections:

**Roles Section** (`roles-section.tsx`):
- Table of roles with permission lists
- Create/edit role dialog (`role-form-dialog.tsx`) with permission checkboxes
- Delete role (with confirmation)
- Immutable/protected roles cannot be modified/deleted

**Users Section** (`users-section.tsx`):
- Table of users with assigned roles
- Assign/unassign role dropdowns per user
- Filter by email

**Permission:** `ManageAccessControl`

---

## Maintenance Page (`maintenance/maintenance-page.tsx`)

Grid of action cards (`maintenance-action-card.tsx`), each triggering a maintenance task:

| Action | Endpoint | Description |
|--------|----------|-------------|
| Delete Tasks | `POST /maintenance/delete-tasks` | Remove old completed/failed/revoked tasks |
| Refresh Analytics | `POST /maintenance/refresh-analytics` | Refresh the `catalog_records_analytics` materialized view |
| Cleanup Locks | `POST /maintenance/cleanup-stale-locks` | Remove stale Redis distributed locks |
| Compact Sectors | `POST /maintenance/compact-sectors` | Recompact MARC sector storage, remove gaps |
| Rebuild Search Vectors | `POST /maintenance/rebuild-search-vectors` | Rebuild full-text search data for all records |

**Permission:** `ManageAppSettings`

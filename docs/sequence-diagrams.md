# Diagrams

All diagrams are PlantUML files in the [`diagrams/`](diagrams/) directory.

## Sequence Diagrams

### 1. Record Sync Flow

Full catalog synchronization from Aleph OAI to application database. Covers
OAI-PMH harvesting, MARC sector storage, distributed locking, analytics updates,
and real-time event publishing.

[`diagrams/record-sync.puml`](diagrams/record-sync.puml)

### 2. Process Records Pipeline

Full processing pipeline: authority linking, comparison, validation. Shows how each record goes through all three stages with result persistence and review outdating.

[`diagrams/process-records.puml`](diagrams/process-records.puml)

### 3. Real-time Notification Flow

How task events reach the client UI. Covers Redis Pub/Sub, WebSocket connection manager with permission-based filtering, and client-side toast/notification handling.

[`diagrams/notification-flow.puml`](diagrams/notification-flow.puml)

### 4. Authentication Flow

Login, token refresh, and request authentication. Covers JWT cookie-based auth with automatic client-side refresh and request queuing.

[`diagrams/authentication.puml`](diagrams/authentication.puml)

## State Diagrams

### 5. Review Lifecycle

How record reviews transition between current, superseded, and outdated states.

[`diagrams/review-lifecycle.puml`](diagrams/review-lifecycle.puml)

## Activity Diagrams

### 6. MARC Sector Storage

How MARC records are stored in and read from compressed sectors.

- **Write path:** [`diagrams/marc-sector-write.puml`](diagrams/marc-sector-write.puml)
- **Read path:** [`diagrams/marc-sector-read.puml`](diagrams/marc-sector-read.puml)

For current entity relationships and schema sources, see
[Persistent data model](entities.md).

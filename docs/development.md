# Development Guide

## Project Overview

This repository consists of four main parts:

1. **App** (`app/`) – the FastAPI web application exposing endpoints and orchestrating business logic.
2. **Workers** (also `app/`) – background tasks (Celery) for asynchronous processing, like fetching and indexing records.
3. **SDK** (`sdk/`) – a reusable MARC comparator library, including validators, comparators, authority linkers, and CLI tools.
4. **Client** (`client/`) – a React frontend (Vite + TypeScript) for browsing records and visualizing results.

---

## Directory & Module Structure

### App Modules

Each feature in the app is organized as a self-contained module:

```
feature/
 ├─ controller.py   # API or task interface
 ├─ service.py      # Business logic
 ├─ models.py       # Pydantic models for validation/serialization of API calls and task data
 ├─ tasks.py        # Background tasks (optional)
 └─ exceptions.py   # Feature-specific errors (optional)
```

**Example: Catalog Records module**

* `catalog_records/controller.py` – exposes REST endpoints or orchestrates task calls.
* `catalog_records/service.py` – logic for fetching, transforming, and validating MARC records.
* `catalog_records/models.py` – defines Pydantic schemas for API payloads and task data.
* `catalog_records/tasks.py` – Celery jobs for record fetching and indexing.
* `catalog_records/exceptions.py` – domain-specific errors.

**Notes:**

* Keep `controller.py` thin: orchestrate services and tasks, handle input/output.
* `service.py` contains the main business logic and may call **adapters** for external systems.
* Use `models.py` **only** for data validation and serialization; do not mix with database models.
* Background jobs in `tasks.py` should leverage services and adapters, not duplicate logic.

#### Special Modules

* **Adapters**
  Encapsulate external integrations to keep the business logic clean. Examples:

  * `aleph_client_registry.py` – Aleph OAI client handling.
  * `database.py` – session creation and queries.
  * `indexer.py` – Elasticsearch indexing abstraction.
  * `logger.py` – structured logging setup.

* **Entities**
  Core domain objects like `CatalogRecord`, `User`, `Task`, and related operations. They should remain business-focused and avoid service-specific logic.

---

## SDK

The SDK is independent of the app:

```
sdk/marc_comparator/
 ├─ validators/          # Validation logic (e.g., Kramerius link validator)
 ├─ comparators/         # Comparisons between MARC records
 ├─ authority_linkers/   # Authority record linking (e.g., knihovny.cz)
 └─ cli/                 # Command-line interface for record processing
```

* Validators follow the `BaseValidator` interface.
* Comparators follow the `BaseComparator` interface.
* Authority linkers follow the `BaseAuthorityLinker` interface.
* CLI commands allow running validations, comparisons, and linking locally against MARC records.

---

## Development Environment

* Python >= 3.12
* Node.js (for client development)
* Virtual environments: `app/.venv/` and `sdk/.venv/`
* Install dependencies:

```bash
make app-env    # Create app virtualenv and install dependencies
make sdk-env    # Create SDK virtualenv and install dependencies
```

* Run app locally (requires infrastructure services):

```bash
make up-infra   # Start PostgreSQL, Redis, etc.
make dev-app    # Start FastAPI app locally
make dev-worker # Start Celery worker locally
```

* Run client in development mode:

```bash
make dev-client # Start Vite dev server with HMR
```

* Run tests:

```bash
make test-integration
```

* Check coverage:

```bash
make coverage-report
```

---

## Docker

Three main containers:

* **App container** – runs FastAPI (`app.Containerfile`).
* **Worker container** – runs Celery tasks (`worker.Containerfile`).
* **Client container** – serves the React frontend via Nginx (`client/Containerfile`).

Build containers:

```bash
make build
```

Start all services:

```bash
make up
```

Stop services:

```bash
make down
```

View logs:

```bash
make logs        # All services
make logs-app    # API server only
make logs-worker # Worker only
make logs-client # Frontend only
```

---

## Branching & Pull Requests

* **Main branch**: `main` – stable production-ready code.
* **Feature branches**: `feature/<short-description>` – implement one feature at a time.
* **Bugfix branches**: `bugfix/<short-description>` – fix a specific issue.

**Pull request guidelines:**

* PR must be based on a feature or bugfix branch.
* All tests must pass before merge.
* Include a description of the change and associated tickets.
* Use meaningful commit messages:

  * `feat: add Kramerius link validator`
  * `fix: handle missing MARC leader`
  * `chore: update dependencies`

---

## Coding Conventions

* Pydantic models for data validation and serialization.
* Keep controllers thin – only orchestrate calls to services.
* Services contain all business logic.
* Tasks only handle async/background execution.
* Adapters abstract external services; avoid business logic here.
* Entities encapsulate the domain model.

---

## Testing

* Unit tests located in `app/tests/unit/`.
* Integration tests located in `app/tests/integration/`.
* Use pytest with `pytest-asyncio` for async tests.
* Mock external services (Aleph, Kramerius) in unit tests.
* Run only a subset of tests:

```bash
make test-integration APP_TEST_TARGET=_smoke
```

---

## Feature Development Workflow

1. Create a feature branch:

   ```bash
   git checkout -b feature/add-marc-validator
   ```
2. Implement controllers, services, models, and optional tasks.
3. Add unit and integration tests.
4. Run tests and ensure coverage.
5. Commit with meaningful messages.
6. Open a pull request for review.
7. Merge into `main` after approval.

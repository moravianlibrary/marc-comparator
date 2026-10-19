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
  * `indexer.py` – Record indexing support.
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

### Local safety and reproducible checks

The default `KUBECONFIG` on this workstation can target production. For local
cluster commands, use Makefile k3d targets without `ALLOW_REMOTE`, or pass
`--kubeconfig .k3d-kubeconfig.yaml` to `kubectl` and `helm`. Check the target
context before any manual cluster mutation. Never drop the working database or
its harvested plugin schemas to troubleshoot an application task. The
`make benchmark` target clears record and task tables; run it only in a
disposable environment.

The local reload sequence is `make helm-reload`. Image import is slow even when
an identical image is already present, so duration does not establish which
code a pod runs. `k3d-load` now imports into every local server and agent node
and fails if any import fails; k3d 5.8.3's helper was observed logging a
missing tar file while returning success. The reload waits for each workload
rollout and leaves the database volume untouched. Check the newest pod and
its image rather than taking `.items[0]` from an unsorted list.

Use `uv run --directory app ...` for app/SDK checks. Do not run bare `uv run`
from sdk/: on this workstation it can select Python 3.14, and lxml then fails
to install. If working directly in sdk/, select Python 3.12 explicitly.

`make check` runs the repository quality gate. A focused unit loop is
`uv run --directory app pytest tests/unit -q`. The full app test suite includes
database and integration tests that need disposable PostgreSQL/Redis test
services; inspect the test fixtures before running those suites against a new
environment. Verify one Alembic head after adding a migration. Do not assume
historical test counts or local deployment results describe the current tree.

### Local migration recovery check (2026-10-16)

The working local database was 13 GB and already at `c4d5e6f7a8b9`. For a
bounded migration check, a separate database held 30 copied validation rows:
10 each with `other_online_resource`, `non_top_level_document`, and
`valid_link`. Only the copy was changed to the preceding revision's values.
`alembic upgrade head` renamed the first reason and moved the second status
to `ForReview`; `alembic downgrade b2c3d4e5f6a7` restored both values; a
second upgrade passed. A `pg_dump -Fc` archive of the sample was restored with
`pg_restore --exit-on-error` into another separate database, where the head
and all 30 rows matched. The local working database was not downgraded or
restored. This checks migration and archive mechanics on representative rows;
it does not measure the time or disk needed to restore a full 13 GB database.

The app pod's `/tmp` is read-only. Stream an archive to the workstation's
`/tmp` with `kubectl --kubeconfig .k3d-kubeconfig.yaml exec ... -- pg_dump
-Fc > /tmp/name.dump`, and stream it back to a *separate empty database* with
`kubectl --kubeconfig .k3d-kubeconfig.yaml exec -i ... -- pg_restore
--exit-on-error < /tmp/name.dump`. Verify the target database name and
revision before running Alembic. Do not restore over the working database.

* Python >= 3.12
* Bun (for client development and builds)
* Virtual environments: `app/.venv/` and `sdk/.venv/`
* Install dependencies:

```bash
make app-env    # Create app virtualenv and install dependencies
UV_PYTHON=python3.12 make sdk-env    # Create SDK virtualenv on Python 3.12
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

## Profiling

Long tasks on this workload have repeatedly turned out to spend their time in
the database rather than in Python, so start with the SQL and only then look at
the interpreter.

### Where the SQL time goes — `pg_stat_statements`

Loaded by default (`cnpg.pgStatStatements`). It accumulates call counts and
timings per normalised statement for as long as the server runs, which is what
makes it usable on a three-hour task: no sampling window to miss.

```bash
make profile-db-reset     # immediately before the run you want to measure
# ... start the task, let it finish ...
make profile-db-report    # worst total time first; PROFILE_TOP=25 by default
```

The `pct` column is a share of everything in the view, so it only means
anything if the counters were reset at the start of the run.

The extension is missing after a database restart, and the cause is CNPG, not
lost data. Its instance manager reconciles on startup — it polls
`pg_extension` in every database and issues `DROP EXTENSION pg_stat_statements`
once, since nothing in the Cluster declares that the extension should exist.
It does not come back for it, so recreating it after the restart holds for the
whole run. `profile-db-reset` does that for you.

`profile-db-report` deliberately does not recreate it: if it is missing at
report time the run straddled a restart, the shared-memory counters went with
it, and an empty table would read as "nothing took any time".

### Where the Python time goes — `py-spy`

py-spy samples a running process without instrumenting it, and it resolves
native frames, so time inside zstd or psycopg shows up as itself rather than
hiding behind one opaque Python call. cProfile is the wrong tool here: it
counts each resumption of a coroutine as a call, which makes async code
unreadable.

Sampling means reading another process's memory, which the default container
capability set forbids. `PROFILE=1` adds `CAP_SYS_PTRACE` to the worker:

```bash
PROFILE=1 make helm-reload     # replaces the worker pod — do it before the run
make profile-worker            # PROFILE_SECONDS=120, writes .profile/*.svg
make profile-worker-dump       # what every pool process is doing right now
```

`profile-worker-dump` is also the quickest answer to "is the task stuck?".

py-spy is fetched on your own machine and copied into the pod, so the shipped
image carries no profiler; the copy is lost whenever the pod is replaced. Note
that the worker has no route to PyPI, so installing it from inside the pod does
not work. Leave `PROFILE` unset for anything but a profiling session.

Read the SVG for shape, not for numbers: it merges boxes by name, so the self
time it appears to show is not attributable. `PROFILE_FORMAT=raw` writes folded
stacks instead, which is what you want as soon as you need a percentage — and
filter those to the stacks containing `process_records`, or the idle pool
children and the master dilute every share you compute.

### Which line issued the query — `adapters.sql_tracing`

The two above each answer half a question. `pg_stat_statements` knows what SQL
ran but nothing about Python; py-spy knows where the wall clock went but
samples too coarsely to catch a query that is individually cheap and made
constantly. Neither says *which line asked for fifty thousand queries*, and on
this workload that has repeatedly been the thing worth knowing: the server is
busy for a few percent of a run, and the cost is the number of round trips
rather than the price of any one of them.

`SQLTRACE=1` makes the worker record, per statement, the application stack that
issued it:

```bash
SQLTRACE=1 make helm-reload    # replaces the worker pod, like PROFILE
```

Each pool child writes its cumulative counters to `/tmp/sql-trace/<pid>.json`
every five seconds. Nothing resets them — a measurement of one stage is the
difference between two dumps, which is also the only honest way to measure a
stage of a worker that is running other things. `scripts/benchmark_pipeline.py`
does that diffing for you.

It is a separate switch from `PROFILE` on purpose: capturing a stack per query
is exactly the kind of overhead that would skew a py-spy sample taken beside
it. Run one or the other, not both.

### Timing the stages against each other — `make benchmark`

`scripts/benchmark_pipeline.py` empties the record tables, syncs a bounded
slice of both catalogues, and then runs each pipeline stage on its own — twice.
The second pass reruns everything with the results already present, which is a
different question with a different answer.

```bash
make k3d-port-forward-up                    # the driver creates tasks over the API
SQLTRACE=1 make helm-reload                 # optional, for the call-site section
make benchmark BENCHMARK_ARGS='--revoke-running'
```

Each stage is bracketed by all three instruments and the task row itself, and
the report lands in `.benchmark/<timestamp>/report.json` after every stage, so
an interrupted run still keeps what it had measured.

What it deletes is `RECORD_TABLES` in the script: records and everything
derived from them, plus task history. Settings, users and roles survive, and so
does harvested plugin data — that lives in the plugins' own Postgres schemas
(`plugin_kramerius_links`, `plugin_marcxml_dump`), which nothing in `public`
can reach. `--no-reset` skips the wipe entirely.

Useful flags: `--stages sync process` to run part of it, `--since-days` for the
sync window, `--py-spy-seconds 60` to take a folded-stack sample inside each
stage.

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

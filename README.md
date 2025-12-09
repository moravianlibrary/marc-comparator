# MARC Comparator Project

The **MARC Comparator Project** is a comprehensive system for **processing MARC bibliographic records**, providing both a **Python SDK** and a full-featured **backend-client application**.

It enables validation, comparison, and authority linking of MARC records, with support for external catalog Aleph.
The **React client** provides an intuitive interface for users to interact with the backend.

---

## Features

* Fetch and process MARC records from external catalog Aleph.
* Compare MARC records using a predefined comparators.
* Validate MARC records with predefined validators (e.g., Kramerius link validator).
* Link MARC records to authority records with use of implemented linkers.
* Provide documented interfaces to allow implementation of custom comparators, validators, and linkers.
* Easy-to-use **CLI** for MARC record inspection, validation, comparing, linking, and exporting.
* **FastAPI backend** with REST API for orchestrating tasks and accessing processed data.
* Background processing using Celery workers for heavy tasks.
* PostgreSQL database for persistent storage.
* Elasticsearch index for fast search and retrieval.
* Redis for task queue and caching.
* Role-based access control (RBAC) for users and permissions.
* **React client** for browsing, searching, and visualizing records and comparison/validation results.

---

## Project Structure

```
app/                        # FastAPI backend and Celery workers
├─ adapters/                # External system adapters (Aleph, DB, Elasticsearch, locks, etc.)
├─ entities/                # Core domain models (DB tables)
├─ common/                  # Shared schema models, utilities, and helpers
├─ access_control/          # RBAC and permission management
├─ auth/                    # Authentication and user management
├─ authority_linking/       # MARC authority linking features
├─ catalog_records/         # Catalog record fetching, syncing, and local storage
├─ comparison/              # MARC record comparison logic
├─ settings/                # Application and task settings management
├─ validation/              # Validation logic for MARC records
├─ config.py                # Environment configuration schemas
├─ app.py                   # FastAPI application entrypoint
├─ app_lifespan.py          # Startup/shutdown lifecycle handlers
├─ app.Containerfile        # Containerfile for FastAPI application image
├─ worker.Containerfile     # Containerfile for Celery worker image
├─ requirements.app.txt     # App dependencies
├─ requirements.worker.txt  # Worker dependencies
├─ Makefile                 # Commands for building, running, and testing
└─ tests/                   # Unit and integration tests

client/                     # React client implementation

sdk/                        # Python SDK for MARC record operations
└─ marc_comparator/
    ├─ validators/          # Validators (e.g., Kramerius links)
    ├─ authority_linkers/   # Authority linkers (e.g., knihovny.cz API)
    ├─ comparators/         # Field and record comparators
    └─ cli/                 # CLI tool for record inspection and processing

deploy/                     # Docker Compose and Helm charts for deployment

demo/                       # Demo configurations, data, and scripts for showcasing usage
```

---

## Application Overview

The **application** allows users to:

* Register and authenticate accounts.
* Add MARC records manually or by uploading files.
* Run validation, authority linking, and comparison tasks on selected records.
* Filter records based on MARC fields or results from validation, linking, and comparison.

The backend handles all data processing and task orchestration, while the **React client** provides a user-friendly interface for visualizing results and managing records.

> Detailed API reference is available [here](docs/api.md).

---

## SDK Overview

The **Python SDK** provides reusable functionality for MARC record processing, including:

* **Validators** – ensure record correctness and consistency (e.g., Kramerius links).
* **Comparators** – compare records or individual fields/subfields with configurable comparators.
* **Authority linkers** – link MARC records to authority records from external sources.

### Implementing Custom Components

The SDK defines clear interfaces and result structures to simplify the creation of custom **validators**, **linkers**, and **comparators**.

> These interfaces are documented in the source code and also described [here](docs/sdk_components.md).

### CLI Commands

The SDK includes a CLI interface implemented with **Typer**, allowing easy usage from command line:

* `print <mrc_files>` – display MARC record contents.
* `to_json <mrc_files>` – convert MARC records to JSON (marcdantic format).
* `validate <mrc_files> [--validator <name>] [--output <path>]` – run validators and export CSV reports.
* `link <linker> <base> <system_number> <mrc_file> <target_base> [--linker-config <path>]` – run authority linking tasks.
* `compare <comparator> <comparator_config> <mrc_file_a> <mrc_file_b>` – run comparisons between two records.

> CLI commands support batch processing and can be integrated into scripts or automated pipelines.

---

## Deployment

* **Docker Compose**: `deploy/docker-compose/docker-compose.yml` sets up **PostgreSQL**, **Elasticsearch**, **Redis**, **backend**, **workers**, and **client**.
* **Helm chart**: `deploy/helms` for Kubernetes deployment (coming soon).
* **Makefile**: provides commands for building Docker images and running the system locally.

---

## Acknowledgment

The software was funded by the Institutional support for long term conceptual development of a research organization (The Moravian Library) by the Czech Ministry of Culture.

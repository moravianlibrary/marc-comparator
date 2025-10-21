# MARC Comparator Project

This project provides a **MARC bibliographic record processing system**, including:

- A **FastAPI application** for REST endpoints and orchestrating tasks.
- **Celery workers** for background processing, fetching and indexing records.
- A **Python SDK** (`marc_comparator_sdk`) for MARC record validation and comparison.

---

## Features

- Fetch and process MARC records from external system Aleph.
- Compare MARC records using a flexible SDK.
- Validate MARC records with custom validators.
- Background processing via Celery.
- Easy-to-use CLI for MARC record inspection and validation.

---

## Project Structure

```
app/                 # FastAPI application and workers
├─ adapters/         # External system adapters (Aleph, DB, Elasticsearch, locks, etc.)
├─ auth/             # Authentication and authorization modules
├─ catalog/          # Catalog feature: MARC record handling
├─ entities/         # Core domain models (DB)
├─ config.py         # Configuration settings
├─ app.py            # FastAPI application entrypoint
├─ app_lifespan.py   # App startup/shutdown lifecycle
└─ tests/            # Integration and unit tests

sdk/                  # Python SDK for MARC record validation and comparison
└─ marc_comparator_sdk/
    ├─ validators/   # Validators (e.g., Kramerius links)
    ├─ comparators/  # Comparators for MARC fields
    └─ cli/          # CLI tool
```

---

## SDK Overview

`marc_comparator_sdk` provides:

- Validators for MARC records (e.g., Kramerius link validator)
- Comparators for record comparison
- CLI for validation and inspection

**CLI Commands:**

- `print <mrc_files>` – print MARC record contents
- `to_json <mrc_files>` – export MARC records to JSON
- `validate <mrc_files>` – run configured validators and export CSV report

---

## License

TBD

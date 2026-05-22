# Marc Comparator SDK

Python library and CLI for parsing, comparing, validating, and linking MARC bibliographic records.

## Overview

The SDK provides three core processing pipelines for MARC records, each built on an extensible plugin architecture:

- **Comparators** -- compare two MARC records field-by-field and produce a similarity score
- **Validators** -- check a single MARC record for correctness and consistency
- **Authority Linkers** -- link a catalog record to an authority record in an external base

All three follow the same pattern: an abstract base class, a concrete implementation, a string enum for dispatch, and a dispatcher dict that maps enum values to classes.

> **SDK vs App**: The SDK supports registering multiple comparators, validators, and linkers. The web app hard-codes which ones to use (currently: Intiim comparator, Kramerius Links validator, Knihovny.cz linker). The SDK is the reusable library; the app is the opinionated deployment.

```
marc_comparator/
├── __init__.py
├── cli/                              # CLI (typer)
│   ├── __init__.py
│   └── __main__.py
├── comparators/
│   ├── __init__.py                   # Comparator enum + dispatcher
│   ├── _base.py                      # BaseComparator ABC, result models
│   ├── intiim.py                     # IntiimComparator wrapper
│   └── intiim_engine/                # Core comparison engine
│       ├── config.py                 # Field roles, thresholds, aggregation constants
│       ├── engine.py                 # Main comparison logic
│       ├── pairer.py                 # Bipartite value pairing (similarity-based)
│       ├── normalizers.py            # Role-based field normalization
│       ├── scoring.py                # Weighted scoring with LP-norm aggregation
│       ├── token_metrics.py          # Similarity ratio + Jaccard metrics
│       ├── llm.py                    # Optional LLM backend (Ollama)
│       ├── llm_verify.py             # LLM verification for edge cases
│       ├── io_marc.py                # MARC record I/O helpers
│       ├── marc21_quality.py         # Field importance weights
│       ├── missing.py                # Configurable missing-field tracking
│       └── checks/                   # Classification checks (run in order)
│           ├── registry.py           # Ordered check list
│           ├── identical.py          # Exact match after normalization
│           ├── typo.py               # High similarity (likely typo)
│           ├── incomplete.py         # Substring/subset coverage
│           ├── nonstandard.py        # Different formatting, same content
│           └── _parts.py             # Part-number handling
├── validators/
│   ├── __init__.py                   # Validator enum + dispatcher
│   ├── _base.py                      # BaseValidator ABC, result models
│   └── kramerius_links.py           # Kramerius link validator (field 856)
└── authority_linkers/
    ├── __init__.py                   # AuthorityLinker enum + dispatcher
    ├── _base.py                      # BaseAuthorityLinker ABC, result model
    └── knihovny_cz_linker.py         # Knihovny.cz authority linker
```

---

## Plugin Architecture

All three subsystems use the same extension pattern:

### 1. Abstract Base Class

Each base class lives in `_base.py` and defines:

- An optional `config_model: type[BaseModel] | None` for Pydantic-based configuration
- An abstract `async run(...)` method with subsystem-specific signature

| Base Class | Method Signature | Returns |
|---|---|---|
| `BaseComparator` | `run(record_a, record_b)` | `RecordComparisonResult` |
| `BaseValidator` | `run(record)` | `List[ValidationResult]` |
| `BaseAuthorityLinker` | `run(base, system_number, record, target_base)` | `AuthorityLink \| None` |

### 2. Enum + Dispatcher

Each `__init__.py` exports:

- A `StrEnum` mapping human-readable names to string keys (e.g. `Validator.KrameriusLinks = "kramerius-links"`)
- A `DISPATCHER` dict mapping enum values to implementation classes
- All public types in `__all__`

### 3. Adding a New Plugin

```python
# 1. Create implementation (e.g. validators/my_validator.py)
class MyValidator(BaseValidator):
    config_model = MyValidatorConfig  # or None

    async def run(self, record: MarcRecord) -> List[ValidationResult]:
        ...

# 2. Register in validators/__init__.py
class Validator(StrEnum):
    KrameriusLinks = "kramerius-links"
    MyValidator = "my-validator"         # add

VALIDATOR_DISPATCHER[Validator.MyValidator] = MyValidator  # add
```

The CLI, web app, and Celery workers all resolve implementations through the dispatcher, so a new plugin is available everywhere once registered.

---

## Comparators

### Intiim Comparator

The only comparator. Compares two MARC records through a multi-stage pipeline:

#### Configuration

```python
class IntiimComparatorConfig(BaseModel):
    ollama_url: str = "http://localhost:11434"
    llm_enabled: bool = False
    nonstandard_llm_enabled: bool = False
    valid_threshold: int = 6       # score below this -> Excellent (0.9-1.0)
    warning_threshold: int = 12    # score below this -> Moderate (0.7-0.9)
```

#### Pipeline

```
Record A + Record B
        │
        ▼
   ┌─────────────┐
   │  Normalize   │  Role-based normalization per (tag, code) pair
   │  by Role     │  e.g. ISBN → stdnum, title → lowercase/strip,
   └──────┬──────┘  name → surname normalization, year → 4-digit
          │
          ▼
   ┌─────────────┐
   │   Pairing    │  Bipartite matching of values using similarity
   │  (pairer)    │  scores (rapidfuzz ratio + token Jaccard)
   └──────┬──────┘
          │
          ▼
   ┌──────────────────────────────────────────────┐
   │  Classification Checks (in order)            │
   │  1. Identical       - exact match            │
   │  2. Typo            - high similarity        │
   │  3. Incomplete      - subset/substring       │
   │  4. NonStandardized - format difference      │
   │  5. Incorrect       - fallback               │
   │  6. Missing         - absent in one side     │
   └──────┬───────────────────────────────────────┘
          │
          ▼
   ┌─────────────┐
   │   Scoring    │  Field weights from marc21_quality.py
   │  (scoring)   │  LP-norm aggregation (p=2) with optional hinge
   └──────┬──────┘  acceleration. Record cap = 30.
          │
          ▼
   ┌─────────────┐
   │  Normalize   │  Piecewise logistic: raw score → 0.0-1.0
   │  Score       │  0→1.0, valid_threshold→0.9, warning→0.7, cap→0.0
   └──────┬──────┘
          │
          ▼
   RecordComparisonResult
     ├── overall_score: float (0.0 - 1.0)
     └── field_results: List[FieldComparisonResult]
           ├── tag, score, explanation
           └── subfield_results: List[SubfieldComparisonResult]
                 └── code, value_a, value_b, score, explanation
```

#### Shared Result Models

Comparison results use enums defined in `_base.py` so they are consistent across all comparator implementations:

**`Explanation`** -- classification of each field/subfield difference:

| Value | Meaning |
|---|---|
| `Identical` | Values match after normalization |
| `NonStandardized` | Same content, different formatting |
| `Typo` | High similarity, likely a typo |
| `Incomplete` | One value is a subset of the other |
| `Incorrect` | Values differ significantly |
| `Missing` | Value present in one record but absent in the other |

**`MatchQuality`** -- overall record match quality derived from the score:

| Value | Score Range |
|---|---|
| `Excellent` | 0.9 - 1.0 |
| `Moderate` | 0.7 - 0.9 |
| `Poor` | 0.0 - 0.7 |

Both are `StrEnum` values, so they serialize to plain strings in JSON.

#### Special Tag Handling

| Tag Group | Tags | Behavior |
|---|---|---|
| UDC | 080 | Matched by subfield `$a` value |
| Headings | 600-655 | Matched by authority ID (`$7`), fallback to normalized `$a` |
| Occurrence | 336-338 | Matched by code (`$b`) and source (`$2`) |
| Aliases | 260/264 | Treated as equivalent (publication info) |
| Ignored | 9XX, 830, 040, 001, 003, 005 | Skipped entirely |

#### Field Roles

Every `(tag, subfield_code)` pair is mapped to a semantic role in `config.py` (`FIELD_ROLE` dict). The role determines which normalizer is applied:

- `isbn` → stdnum ISBN normalization
- `title` → lowercase, strip punctuation
- `name` → surname normalization
- `year` → extract 4-digit year
- `udc` → UDC-specific normalization
- `authority_id` → strip formatting
- etc.

#### Score Interpretation

| Overall Score | Match Quality | Meaning |
|---|---|---|
| 0.9 - 1.0 | Excellent | Records are essentially the same |
| 0.7 - 0.9 | Moderate | Notable differences but same work |
| 0.0 - 0.7 | Poor | Significant differences |

---

## Validators

### Kramerius Links Validator

Validates MARC field 856 (Electronic Location) for Kramerius digital library links.

#### Configuration

```python
class KrameriusLinksValidatorConfig(BaseModel):
    url_to_pid_pattern: str = r"https?://[^/]+/mzk/uuid/(uuid:[0-9a-fA-F-]+)"
    link_text_pattern: str = r"Digitalizovaný dokument"
    kramerius_host: str = "https://api.kramerius.mzk.cz/search"
    solr_cloud: bool = False
```

#### Checks Performed

1. URL format validation (`$u` subfield matches configured pattern)
2. Link text validation (`$y` subfield matches expected text)
3. Cross-reference with Kramerius API (verifies the linked PID exists)
4. Level and model consistency checks

#### Result Statuses

| Status | Meaning |
|---|---|
| `Valid` | Link is correct and verified |
| `ForReview` | Potential issue requiring human review |
| `Invalid` | Link is broken or incorrect |
| `AdditionalInfo` | Extra context (not an error) |

---

## Authority Linkers

### Knihovny.cz Linker

Links catalog records to authority records via the knihovny.cz deduplication API.

#### Configuration

```python
class KnihovnyCZLinkerConfig(BaseModel):
    api_url: str = "https://www.knihovny.cz/api/v1"
    base_mappings: dict  # Maps source bases to target base patterns
```

#### Process

1. Resolve source base to knihovny.cz record via configured base mappings
2. Query knihovny.cz deduplication API
3. Retrieve the matching authority MARC record
4. Return `AuthorityLink` with base, system number, record, and confidence

#### get_target_bases

Class method that returns the list of authority bases this linker can target, derived from the configuration's base mappings.

---

## CLI

Installed as `marc-comparator` command via the `[project.scripts]` entry point.

### Commands

#### `print` -- Display MARC record contents

```bash
marc-comparator print record.mrc [record2.mrc ...]
```

Human-readable output: leader, fixed fields, variable fields with indicators and subfields.

#### `to-json` -- Convert MRC to JSON

```bash
marc-comparator to-json record.mrc
```

Writes `record.json` alongside the input file using marcdantic's JSON serialization.

#### `validate` -- Run validators

```bash
marc-comparator validate record.mrc \
  --validator kramerius-links \
  --config validation.json \
  --output report.csv
```

Runs specified validators and writes results to CSV with columns: path, validator, tag, codes, status, reason, details, hint.

#### `compare` -- Compare two records

```bash
marc-comparator compare intiim comparison.json record_a.mrc record_b.mrc
```

Prints overall score and per-field/subfield comparison results.

#### `link` -- Link to authority record

```bash
marc-comparator link knihovny-cz MZK01 000123456 record.mrc SKC \
  --linker-config authority-linking.json
```

Attempts to find a matching authority record and prints the result.

### Configuration Loading

All CLI commands that accept `--config` support an optional top-level key wrapper. For example, a validation config can be either:

```json
{ "url_to_pid_pattern": "...", "kramerius_host": "..." }
```

or wrapped:

```json
{ "kramerius-links": { "url_to_pid_pattern": "...", "kramerius_host": "..." } }
```

The CLI auto-detects the wrapper and unwraps it before passing to the Pydantic config model.

---

## Dependencies

| Package | Purpose |
|---|---|
| `marcdantic` | MARC record parsing (MRC/XML) and Pydantic models |
| `pydantic` | Configuration and result model validation |
| `typer` | CLI framework |
| `pymarc` | Alternative MARC I/O (used by intiim_engine) |
| `rapidfuzz` | String similarity metrics (ratio, partial_ratio) |
| `python-stdnum` | ISBN/ISSN normalization and validation |
| `httpx` | Async HTTP client (Kramerius API, knihovny.cz API) |
| `kramerius` | Kramerius API client library |
| `solrify` | Solr query building |
| `lxml` | XML parsing |

---

## Integration with Web App

The web app (`/app`) imports the SDK as a Python package:

```python
from marc_comparator.comparators import Comparator, COMPARATOR_DISPATCHER
from marc_comparator.validators import Validator, VALIDATOR_DISPATCHER
from marc_comparator.authority_linkers import AuthorityLinker, AUTHORITY_LINKER_DISPATCHER
```

Celery workers instantiate comparators/validators/linkers with configuration from the database settings, then call `await instance.run(...)` to process records. Results are stored as JSONB in PostgreSQL.

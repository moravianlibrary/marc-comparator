# SDK Components

The SDK defines clear interfaces and result structures to simplify the creation of custom **validators**, **authority linkers**, and **comparators** for MARC records.

These interfaces are designed for **extensibility and consistency**, ensuring that custom implementations integrate seamlessly with the platform.

---

## **Validators**

### Base Interface

**Class:** `BaseValidator`

**Description:** Abstract base class for implementing MARC record validators. Validators inspect a single MARC record and return structured results.

**Method:**

```python
async def run(self, record: MarcRecord) -> List[ValidationResult]
```

**Input:**

* `record` (`MarcRecord`) – The MARC record to validate.

**Output:**

* `List[ValidationResult]` – A list of validation results, where each result contains:

  * `target` (`ValidationTarget`) – The MARC field/subfields being validated.
  * `status` (`ValidityStatus`) – One of `Valid`, `Invalid`, `Warning`, `Info`.
  * `reason` (optional) – Short explanation of the result.
  * `details` (optional) – Additional context.
  * `hint` (optional) – Guidance for fixing issues.

**Implementation Notes:**

* Always include meaningful `reason` and, if possible, a `hint` to aid in automated or manual fixing.
* `reason` should be ideally drawn from a predefined set of standard values. This ensures that validation results can be efficiently indexed, searched, and aggregated in Elasticsearch.
* Can define `config_model` (`pydantic.BaseModel`) to allow configurable parameters for the validator.

---

## **Authority Linkers**

### Base Interface

**Class:** `BaseAuthorityLinker`

**Description:** Abstract base class for linking a catalog MARC record to an authority record.

**Method:**

```python
async def run(
    base: str,
    system_number: str,
    record: MarcRecord,
    target_base: str,
) -> AuthorityLink | None
```

**Input:**

* `record` (`MarcRecord`) – Catalog record to link.
* `base` (str) – Source catalog base identifier.
* `system_number` (str) – Identifier of the catalog record.
* `target_base` (str) – Authority base to link against (e.g., MZK01, KNAV).

**Output:**

* `AuthorityLink` or `None`

  * If successful, contains:

    * `base` – Authority base.
    * `system_number` – Authority system number.
    * `record` – Linked MARC authority record.
    * `confidence` (optional) – Numeric confidence score (0–1).
  * Return `None` if no suitable link is found.

**Implementation Notes:**

* Confidence scores should be **normalized between 0 and 1**.
* Consider caching or batching lookups for efficiency when querying external authority sources.
* Can define `config_model` (`pydantic.BaseModel`) for adjustable parameters (e.g., matching thresholds, endpoints).

---

## **Comparators**

### Base Interface

**Class:** `BaseComparator`

**Description:** Abstract base class for comparing two MARC records. Produces a structured similarity result for automated matching or scoring.

**Method:**

```python
async def run(record_a: MarcRecord, record_b: MarcRecord) -> RecordComparisonResult
```

**Input:**

* `record_a` (`MarcRecord`) – First record for comparison.
* `record_b` (`MarcRecord`) – Second record for comparison.

**Output:** `RecordComparisonResult`

* `overall_score` (float) – Overall similarity score.
* `summary` (optional) – Human-readable summary of differences.
* `field_results` (optional) – List of `FieldComparisonResult`, each containing:

  * `tag` – MARC field tag.
  * `score` – Field similarity score.
  * `explanation` (optional) – Text explaining the field-level score.
  * `details` (optional) – Additional context for the comparison.
  * `subfield_results` (optional) – List of `SubfieldComparisonResult` for each subfield, containing:

    * `code` – MARC subfield code.
    * `score` – Subfield similarity score.
    * `explanation` (optional) – Explanation for the subfield score.
    * `details` (optional) – Additional context for the subfield comparison.
    
**Implementation Notes:**

* Comparators should handle **missing or optional fields** gracefully.
* Scores should be **normalized** and comparable across records.
* Use meaningful `explanation` and `details` fields to aid interpretation.
* Can define `config_model` (`pydantic.BaseModel`) for thresholds, weights, or custom scoring rules.

---

## **General Considerations When Implementing SDK Components**

1. **Asynchronous Execution:** All `run` methods are `async`; ensure proper handling of I/O operations.
2. **Idempotency:** Validators, linkers, and comparators should produce consistent results for the same inputs.
3. **Configuration:** Use `config_model` to allow users to customize behavior without modifying code.
4. **Error Handling:** Return structured results rather than raising exceptions whenever possible; unexpected failures should be logged and wrapped in results if needed.
5. **Documentation:** Clearly document input expectations and output formats for each custom implementation.

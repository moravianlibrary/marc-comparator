# Marc Comparator SDK

A Python SDK and CLI for working with MARC bibliographic records, comparing MARC records, and validating MARC records.

---

## Library

### Comparators

The SDK supports building **comparators** for MARC records.
*Currently under development.*

#### Interface

*Currently under development.*

---

### Validators

Validators check MARC records for correctness, completeness, and consistency.

#### Base Interface

All validators inherit from a `BaseValidator` class.
They implement an asynchronous `run(record: MarcRecord)` method, which returns a list of `ValidationResult` objects.

#### Validation Results

* **ValidityStatus**: `Valid`, `Invalid`, `Warning`, or `Info`
* **ValidationField**: Target field (tag and optional subfields)
* **ValidationResult**: Includes status, reason, details, and hints for corrections.

#### Example Validator: `KrameriusLinksValidator`

* Checks the presence and correctness of Kramerius links in MARC records (field `856`).
* Verifies `$u` URLs and `$y` link text against patterns.
* Cross-references links with the Kramerius API.
* Provides detailed feedback and hints for fixes.

---

## Command Line Interface (CLI)

The SDK provides a CLI for inspecting, converting, and validating MARC records.

### Commands

* **print**
  Print MARC record contents:

  ```bash
  marc-comparator print /path/to/record.mrc
  ```

* **to-json**
  Convert MARC records to JSON:

  ```bash
  marc-comparator to-json /path/to/record.mrc
  ```

* **validate**
  Validate MARC records using specified validators:

  ```bash
  marc-comparator validate /path/to/record.mrc --validator kramerius-links
  ```

### Validators

* `kramerius-links`: Ensures MARC 856 fields contain valid Kramerius links.

### Output

Validation results are saved in **CSV** format (default: `report.csv`) with the following fields:

* File path
* Validator name
* MARC field tag
* Subfield codes
* Status
* Reason
* Details
* Hint for corrections

---

## MARC Record Handling

* Uses **Marcdantic** for parsing MARC records from MRC or XML.
* Provides convenient accessors for:

  * Leader fields
  * Fixed and variable fields
  * Numbers, codes, titles, issues, and local fields

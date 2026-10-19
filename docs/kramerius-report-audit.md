# Kramerius report audit, October 2026

This is dated evidence for the uncommitted report changes prepared on
2026-10-15, not a claim that a newly generated report has passed. Reproduce
the checks against the artifact selected for use before importing any `.seq`.

## Why the full revalidation was needed

The earlier report mixed findings from several validator generations. A reason
rename could update stored labels but could not produce findings the old
validator never checked. A full validation pass ran on 2026-10-15 22:00 to
2026-10-16 00:08, followed by report regeneration. According to the historical
audit, it processed the corpus and rebuilt analytics. The working database and
artifact still need verification against the current tree.

## Rules the report must preserve

- An Aleph 856 replacement block must preserve unrelated fields, subfields,
  values, indicator bytes, field order and meaningful `$x`/`$z` volume data.
  Newly repaired `$u`/`$y` fields may change only as their rules specify.
- A record must appear in at most one `.seq` output. A repair includes any
  normalization that is due for the same record. No no-op normalization block
  should be emitted.
- New links must not duplicate an existing byte-identical URL or silently
  collapse distinct volume links onto one parent. Non-top-level documents go
  to review rather than an automatic parent rewrite.
- Malformed URLs and ambiguous matches go to review with their literal source
  values; the generator must not guess cataloguer intent. The three historical
  corrupt `$u` cases require manual source correction.
- Delete output applies only where the record has exactly one 856 and that
  link is confirmed dead. Delete system numbers must not overlap `.seq`.
- Review CSV row counts must reconcile with their validation reasons; report
  generation must produce no unhandled record errors.

The `link_text_pattern` deliberately remains a case-sensitive prefix match.
A non-matching `$y` may be repaired using the configured `link_text`; a
matching one and any unrelated 856 data must be preserved.

## Historical result and reproduction

The previous field-level audit reconstructed originals from sector storage
for all 40,387 affected records. It reported zero lost subfields, changed
unrelated values or indicators, overlapping output records, and rule-simulation
deviations across 30,530 repair records. It reported zero newly created
byte-identical duplicate `$u` values and zero no-op normalization blocks.
Nine remaining same-document pairs were explained: six links to other digital
libraries with the same PID, and three malformed source URLs reported for
review. These counts are dated results, not acceptance of a future artifact.

The retained audit tools are
[`scripts/audit_kramerius_fields.py`](../scripts/audit_kramerius_fields.py),
[`scripts/audit_kramerius_rules.py`](../scripts/audit_kramerius_rules.py), and
[`scripts/export_kramerius_audit_inputs.py`](../scripts/export_kramerius_audit_inputs.py).
The first two run offline. The exporter reads MARC and validation rows from the
app database and does not write to it. It must run with the same database state
and validator settings that generated the report, and must be given that
report's directory. Its output is the two input snapshots below; it requires
the app's normal database environment and `PYTHONPATH=app` when run from the
repository root.

The October 16 snapshot and corrected report are still in this local scratch
directory:

```text
/tmp/claude-1000/-home-robert-code-work-github-com-moravianlibrary-marc-comparator/e131f084-043b-47a2-8bf7-6fbca3b2a00f/scratchpad
```

From the repository root, set `AUDIT_SNAPSHOT_DIR` to that directory and run:

```sh
python3 scripts/audit_kramerius_fields.py "$AUDIT_SNAPSHOT_DIR" "$AUDIT_SNAPSHOT_DIR/newreport2"
python3 scripts/audit_kramerius_rules.py "$AUDIT_SNAPSHOT_DIR" "$AUDIT_SNAPSHOT_DIR/newreport2"
sha256sum "$AUDIT_SNAPSHOT_DIR/orig856_new.json" "$AUDIT_SNAPSHOT_DIR/findings2.psv" "$AUDIT_SNAPSHOT_DIR/newreport2.zip"
```

For a fresh report, export its inputs before the underlying database changes:

```sh
PYTHONPATH=app app/.venv/bin/python scripts/export_kramerius_audit_inputs.py REPORT_DIR SNAPSHOT_DIR
python3 scripts/audit_kramerius_fields.py SNAPSHOT_DIR REPORT_DIR
python3 scripts/audit_kramerius_rules.py SNAPSHOT_DIR REPORT_DIR
```

The exporter requires database access and reads only the report's system
numbers. The audit scripts reject overlapping output sets, lost/changed
unrelated subfields, changed indicators, no-op rewrites, unexpected repair
field counts and newly introduced byte-identical `$u` values. They also print
changes requiring human interpretation, including removed fields and
same-document links; exit code zero does not approve those automatically.
Review every such line against the source and the review CSVs.

On 2026-10-16, these commands passed against `newreport2/`. The ZIP contained
13 files and every ZIP entry matched its directory copy byte-for-byte. SHA-256:

| Input/artifact | Digest |
| --- | --- |
| `orig856_new.json` | `350456d275e55be669ae71f675d47b00fa913fb5207edd7a8a75b5b1de8f5b8c` |
| `findings2.psv` | `41aef7312b4ac357628d0ad55ccfc2b8f0b7d2ba60f6d5a800c749bb3a37be8a` |
| `newreport2.zip` | `3015b6ec7dd066349a2c8e046a6f0d09de31a21cc6e470c5c540523f91271601` |

The offline rule simulation reported 0 field-count deviations and 0 newly
introduced byte-identical `$u` values. The field audit reported 11 one-field
deletions, 1,734 `$y` changes during normalization, 7 `$y` changes on repair
records, and 9 same-document pairs. Those nine were reviewed as six links
into another library sharing our PID and three malformed source URLs. The
expected review rows must accompany the actual artifact used.

The earlier files in `~/inbox` were identified as the defective 2026-10-14
generation. They must not be silently replaced or distributed. Moving or
replacing them requires the user's choice.

"""Export read-only MARC and validation snapshots for the Kramerius report audit.

Run inside the application environment with its normal database configuration.
The report directory must be the artifact generated from that same database
state. This script does not modify the database.
"""

import json
import sys
from pathlib import Path

from adapters.database import SessionLocal
from adapters.marc_sectors import read_marc_many, read_stored_marc
from entities.catalog_record import CatalogRecord
from entities.validation import Validation

BASES = ("MZK01", "MZK03")


def report_records(report_dir: Path) -> dict[str, list[str]]:
    by_base: dict[str, set[str]] = {base: set() for base in BASES}
    for base in BASES:
        for kind in ("repair", "normalization"):
            path = report_dir / f"aleph_{kind}_{base}.seq"
            for line in path.read_text(encoding="utf-8").splitlines():
                by_base[base].add(line.split(" ", 1)[0])
        path = report_dir / f"aleph_delete_856_{base}.txt"
        by_base[base].update(path.read_text().split())
    return {base: sorted(values) for base, values in by_base.items()}


def main(report_dir: Path, output_dir: Path) -> None:
    selected = report_records(report_dir)
    originals = {}
    findings = []
    output_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as session:
        for base, sysnos in selected.items():
            for start in range(0, len(sysnos), 1000):
                chunk = sysnos[start : start + 1000]
                raw_by_sysno = read_marc_many(session, base, chunk)
                missing = set(chunk) - raw_by_sysno.keys()
                if missing:
                    raise ValueError(f"MARC missing for {base}: {sorted(missing)[:10]}")

                for sysno in chunk:
                    record = read_stored_marc(raw_by_sysno[sysno])
                    fields = record.variable_fields.query_fields('.["856"][]?')
                    originals[f"{base}|{sysno}"] = [
                        {
                            "ind1": field.ind1,
                            "ind2": field.ind2,
                            "subfields": field.subfields,
                        }
                        for field in fields
                    ]

                ids = [CatalogRecord.generate_id(base, sysno) for sysno in chunk]
                rows = (
                    session.query(Validation)
                    .filter(
                        Validation.catalog_record_id.in_(ids),
                        Validation.validator == "kramerius-links",
                    )
                    .all()
                )
                for row in rows:
                    result = row.validation_result
                    if result.reason is None:
                        continue
                    sysno = row.catalog_record_id.removeprefix(f"{base}-")
                    params = result.params or {}
                    findings.append(
                        "|".join(
                            (
                                base,
                                sysno,
                                result.reason,
                                str(result.target.field_index)
                                if result.target.field_index is not None
                                else "-",
                                str(params.get("pid", "")),
                                str(params.get("top_level_pid", "")),
                            )
                        )
                    )

    (output_dir / "orig856_new.json").write_text(
        json.dumps(originals, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "findings2.psv").write_text("\n".join(sorted(findings)) + "\n")
    print(f"Exported {len(originals)} records and {len(findings)} findings to {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: export_kramerius_audit_inputs.py REPORT_DIR OUTPUT_DIR")
    main(Path(sys.argv[1]), Path(sys.argv[2]))

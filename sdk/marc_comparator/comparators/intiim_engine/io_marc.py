from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pymarc import MARCReader, Record


def _as_dict(rec: Record) -> dict:
    d: dict = {"leader": rec.leader, "fields": []}

    for f in rec.get_fields():
        if f.is_control_field():
            d["fields"].append({f.tag: f.data})
        else:
            subfields = []

            if f.subfields and hasattr(f.subfields[0], "code") and hasattr(f.subfields[0], "value"):
                for sf in f.subfields:
                    subfields.append({sf.code: sf.value})
            else:
                it = iter(f.subfields)
                for code, value in zip(it, it):
                    subfields.append({str(code): str(value)})

            d["fields"].append(
                {
                    f.tag: {
                        "ind1": f.indicator1 if f.indicator1 is not None else " ",
                        "ind2": f.indicator2 if f.indicator2 is not None else " ",
                        "subfields": subfields,
                    }
                }
            )
    return d


def load_records(
    path_or_obj: str | Path | list[dict[str, Any]] | dict[str, Any],
) -> list[dict[str, Any]]:
    if isinstance(path_or_obj, (list, dict)):
        return path_or_obj if isinstance(path_or_obj, list) else [path_or_obj]
    path = Path(path_or_obj)
    if path.suffix.lower() in {".mrc", ".marc"}:
        recs: list[dict[str, Any]] = []
        with open(path, "rb") as fh:
            reader = MARCReader(fh, to_unicode=True, force_utf8=True, utf8_handling="ignore")
            for rec in reader:
                if rec is None:
                    continue
                recs.append(_as_dict(rec))
        return recs
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]


def load_records_from_bytes(data: bytes) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    reader = MARCReader(data, to_unicode=True, force_utf8=True, utf8_handling="ignore")
    for rec in reader:
        if rec is None:
            continue
        recs.append(_as_dict(rec))
    if not recs:
        raise ValueError("No MARC records found in bytes payload.")
    return recs

"""Shared reading for the Kramerius report audits.

The two audit scripts beside this one answer different questions — one
compares emitted 856 blocks against the originals field by field, the other
re-derives what the repair rules should have produced — but they read the
same two snapshot files and the same `.seq` format to do it. That reading
lives here so the filenames and the line format are written once.

Deliberately *not* here: anything that encodes a validator rule. The rule
simulation reimplements those on purpose, and sharing them with the code
under audit would make the audit prove nothing. See the header of
`audit_kramerius_rules.py`.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

#: The two files `export_kramerius_audit_inputs.py` writes, named once.
SNAPSHOT_FIELDS_FILE = "orig856_new.json"
SNAPSHOT_FINDINGS_FILE = "findings2.psv"

#: A Kramerius persistent identifier, wherever it appears.
PID = re.compile(
    r"uuid:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

#: One 856 as the audits hold it: both indicator bytes and ordered subfields.
SeqField = tuple[str, str, list[tuple[str, str]]]


def snapshot_and_report_args(script: str) -> tuple[Path, Path]:
    """The two directories every audit takes, or a usage message.

    Positional `sys.argv` reads gave a bare `IndexError` when either was
    left off, which says nothing about what was wanted.
    """

    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {script} SNAPSHOT_DIR REPORT_DIR")

    return Path(sys.argv[1]), Path(sys.argv[2])


def load_original_fields(snapshot_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """The pre-report 856 blocks, keyed `BASE|SYSNO`."""

    return json.loads((snapshot_dir / SNAPSHOT_FIELDS_FILE).read_text())


def original_fields(originals: dict[str, list[dict[str, Any]]], key: str) -> list[SeqField]:
    """One record's original 856s, in the same shape `load_seq` returns."""

    return [
        (
            field["ind1"] or " ",
            field["ind2"] or " ",
            [(code, value) for code, values in field["subfields"].items() for value in values],
        )
        for field in originals.get(key, [])
    ]


def parse_seq_line(rest: str) -> SeqField:
    """`85641 L $$uX$$yY` to its indicators and subfields."""

    head, _, body = rest.partition(" L ")
    tag, ind1, ind2 = head[:3], head[3], head[4]
    if tag != "856":
        raise ValueError(f"expected an 856 line, got {rest!r}")

    return ind1, ind2, [(part[0], part[1:]) for part in body.split("$$")[1:]]


def load_seq(path: Path | str) -> dict[str, list[SeqField]]:
    """An Aleph `.seq` file as the 856 blocks it carries, keyed by system number."""

    blocks: dict[str, list[SeqField]] = collections.defaultdict(list)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        sysno, rest = line.split(" ", 1)
        blocks[sysno].append(parse_seq_line(rest))

    return blocks

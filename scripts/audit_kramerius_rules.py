"""Simulate the current repair rules and compare with what was emitted.

The rules below — `OWN`, `CANON_PATH`, `NONCANON_PATH`, `REPAIR`,
`linked_documents`, `drop_redundant` — are a deliberate second implementation
of what `marc_comparator.validators.kramerius_links` does, written from the
specification rather than imported from it. An audit that calls the code it
audits agrees with that code by construction and proves nothing.

The cost of that choice is drift: nothing here breaks when the validator
changes. `app/tests/unit/test_kramerius_audit_constants.py` pins the one part
that is a plain shared constant, `REPAIR`, so a change to the validator's
reason set fails a test rather than quietly changing what this script means.
The patterns are configurable settings and cannot be pinned the same way —
re-read them against the deployed configuration before trusting a run.
"""

import collections
import re

from kramerius_audit_io import (
    PID,
    SNAPSHOT_FINDINGS_FILE,
    load_original_fields,
    load_seq,
    original_fields,
    snapshot_and_report_args,
)

SP, R = snapshot_and_report_args("audit_kramerius_rules.py")
orig = load_original_fields(SP)
CANON = "https://www.digitalniknihovna.cz/mzk/uuid/"
OWN = re.compile(r"^https?://(?:www\.)?(?:digitalniknihovna\.cz/mzk|kramerius\.mzk\.cz)(?=[/?#]|$)")
CANON_PATH = re.compile(r"^/mzk/uuid/(uuid:[0-9a-fA-F-]{36})$")
NONCANON_PATH = re.compile(r"^/mzk/(?:periodical|view|search)/.*?(uuid:[0-9a-fA-F-]{36})")
REPAIR = {"missing_link_in_marc", "link_not_found", "non_canonical_url_not_found"}


def linked_documents(subs):
    """PIDs this field links, as the validator counts them: ours only."""
    out = set()
    for c, v in subs:
        if c != "u" or not OWN.match(v):
            continue
        path = v.split("://", 1)[1]
        path = path[path.index("/") :] if "/" in path else ""
        m = CANON_PATH.match(path) or NONCANON_PATH.match(path)
        if m:
            out.add(m.group(1))
    return out


def drop_redundant(fields):
    kept = []
    for subs in fields:
        docs = linked_documents(subs)
        if not docs:
            kept.append(subs)
            continue
        mine = set(subs)
        resolved = False
        for i, other in enumerate(kept):
            if not (docs & linked_documents(other)):
                continue
            theirs = set(other)
            if mine <= theirs:
                resolved = True
                break
            if theirs <= mine:
                kept[i] = subs
                resolved = True
                break
        if not resolved:
            kept.append(subs)
    return kept


f = collections.defaultdict(list)
for line in (SP / SNAPSHOT_FINDINGS_FILE).read_text().splitlines():
    line = line.rstrip("\n")
    if not line.strip():
        continue
    base, sysno, reason, fi, pid, top = line.split("|")
    f[f"{base}|{sysno}"].append((reason, fi, pid, top))


load = load_seq


def ofields(k):
    """This audit compares subfields only; the field audit checks indicators."""

    return [subs for _ind1, _ind2, subs in original_fields(orig, k)]


bad = []
new_dup_u = []
new_dup_pid = []
for base in ("MZK01", "MZK03"):
    deleted = {
        line.strip()
        for line in (R / f"aleph_delete_856_{base}.txt").read_text().splitlines()
        if line.strip()
    }
    blocks = load(f"{R}/aleph_repair_{base}.seq")
    for sysno in sorted(set(blocks) | deleted):
        key = f"{base}|{sysno}"
        before = ofields(key)
        after = blocks.get(sysno, [])
        fs = [x for x in f[key] if x[0] in REPAIR]
        removals = {int(fi) for r, fi, _, _ in fs if r.endswith("not_found") and fi != "-"}
        kept = drop_redundant([fl for i, fl in enumerate(before) if i not in removals])
        existing_us = {v for fl in kept for c, v in fl if c == "u"}
        existing_pids = {p for fl in kept for p in linked_documents(fl)}
        n = len(kept)
        for r, _, p, _ in fs:
            if r != "missing_link_in_marc":
                continue
            newu = CANON + p
            if newu in existing_us or p in existing_pids:
                continue
            existing_us.add(newu)
            existing_pids.add(p)
            n += 1
        if n != len(after):
            bad.append((key, n, len(after)))

        au = [v for fl in after for c, v in fl[2] if c == "u"]
        bu = [v for fl in before for c, v in fl if c == "u"]
        if (len(au) - len(set(au))) > (len(bu) - len(set(bu))):
            new_dup_u.append(key)
        ap = [m.group(0) for u in au for m in [PID.search(u)] if m]
        bp = [m.group(0) for u in bu for m in [PID.search(u)] if m]
        if (len(ap) - len(set(ap))) > (len(bp) - len(set(bp))):
            new_dup_pid.append(key)

print(f"repair records whose field count differs from a faithful simulation: {len(bad)}")
for b in bad[:10]:
    print("   ", b)
print(f"records that gained a byte-identical duplicate $u: {len(new_dup_u)} {new_dup_u[:8]}")
print(f"records that gained a same-document duplicate:     {len(new_dup_pid)} {new_dup_pid[:10]}")

if bad or new_dup_u:
    raise SystemExit("Audit failed: repair simulation or duplicate URL invariant")

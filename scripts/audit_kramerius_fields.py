"""Field-level audit: what the report did to the original 856 blocks.

Rebuilds each affected record's 856s from the snapshot and compares them with
what the report emitted, reporting anything the report had no licence to
change — lost subfields, altered values, moved indicators, no-op rewrites and
newly duplicated links — plus the disjointness of the three output sets.

Lines about removed fields and same-document pairs need a human read and are
printed rather than failed on; the exit code covers only what is
unambiguously wrong.
"""

import collections

from kramerius_audit_io import (
    PID,
    load_original_fields,
    load_seq,
    original_fields,
    snapshot_and_report_args,
)

SNAPSHOT_DIR, REPORT_DIR = snapshot_and_report_args("audit_kramerius_fields.py")
orig = load_original_fields(SNAPSHOT_DIR)


def orig_fields(key):
    return original_fields(orig, key)


def sig(f):
    return (f[0], f[1], tuple(f[2]))


def pids(f):
    return {m.group(0) for c, v in f[2] if c == "u" for m in [PID.search(v)] if m}


report = collections.Counter()
examples = collections.defaultdict(list)


def note(k, ex):
    report[k] += 1
    if len(examples[k]) < 3:
        examples[k].append(ex)


for base in ("MZK01", "MZK03"):
    for kind in ("repair", "normalization"):
        blocks = load_seq(f"{REPORT_DIR}/aleph_{kind}_{base}.seq")
        for sysno, emitted in blocks.items():
            key = f"{base}|{sysno}"
            before = orig_fields(key)
            k = f"{kind}"

            if [sig(f) for f in emitted] == [sig(f) for f in before]:
                note(f"{k}: emitted block IDENTICAL to original (no-op rewrite)", key)

            # which original fields survived unchanged / changed / vanished
            before_sig = [sig(f) for f in before]
            emit_sig = [sig(f) for f in emitted]
            kept_exact = sum(1 for s in before_sig if s in emit_sig)
            lost = len(before) - kept_exact
            added = len(emitted) - kept_exact

            # subfield-level: for each original field, find its counterpart by
            # index position among survivors is unreliable, so match on $u pid
            # or on the non-u subfields.
            for i, bf in enumerate(before):
                bpids = pids(bf)
                bnonu = tuple(s for s in bf[2] if s[0] != "u")
                match = None
                for ef in emitted:
                    if sig(ef) == sig(bf):
                        match = ef
                        break
                if match is None:
                    for ef in emitted:
                        if bpids and pids(ef) & bpids:
                            match = ef
                            break
                if match is None:
                    for ef in emitted:
                        if bnonu and tuple(s for s in ef[2] if s[0] != "u") == bnonu:
                            match = ef
                            break
                if match is None:
                    note(
                        f"{k}: original 856 has no counterpart in output (removed)",
                        f"{key} field#{i}",
                    )
                    continue
                if (match[0], match[1]) != (bf[0], bf[1]):
                    note(f"{k}: indicators changed", f"{key} {bf[:2]}->{match[:2]}")
                bcodes = collections.Counter(c for c, _ in bf[2])
                ecodes = collections.Counter(c for c, _ in match[2])
                for c in bcodes:
                    if ecodes[c] < bcodes[c]:
                        note(f"{k}: subfield ${c} lost from a field", f"{key} field#{i}")
                # non-u, non-y subfield values must be byte-identical
                for c, v in bf[2]:
                    if c in ("u", "y"):
                        continue
                    if (c, v) not in match[2]:
                        note(f"{k}: subfield ${c} value changed", f"{key} ${c}={v!r}")
                for c, v in bf[2]:
                    if c == "y" and (c, v) not in match[2]:
                        note(f"{k}: existing $y value changed", f"{key} $y={v!r}")

            # duplicate documents inside the emitted block
            allp = [p for f in emitted for p in pids(f)]
            bp = [p for f in before for p in pids(f)]
            dup_after = len(allp) - len(set(allp))
            dup_before = len(bp) - len(set(bp))
            if dup_after > dup_before:
                note(f"{k}: output links the same document twice (new duplicate)", key)
            elif dup_after > 0:
                note(
                    f"{k}: output links the same document twice (already in source)",
                    key,
                )

            # subfield order: $y should sit right after $u
            for ef in emitted:
                codes = [c for c, _ in ef[2]]
                if "u" in codes and "y" in codes and codes.index("y") != codes.index("u") + 1:
                    note(f"{k}: $y not directly after $u", f"{key} {codes}")

# delete list sanity
for base in ("MZK01", "MZK03"):
    for sysno in (REPORT_DIR / f"aleph_delete_856_{base}.txt").read_text().splitlines():
        sysno = sysno.strip()
        if not sysno:
            continue
        key = f"{base}|{sysno}"
        n = len(orig_fields(key))
        note(f"delete list: record had {n} 856 field(s), all dropped", key)

for base in ("MZK01", "MZK03"):
    repair = set(load_seq(f"{REPORT_DIR}/aleph_repair_{base}.seq"))
    normalization = set(load_seq(f"{REPORT_DIR}/aleph_normalization_{base}.seq"))
    deleted = {
        s.strip()
        for s in (REPORT_DIR / f"aleph_delete_856_{base}.txt").read_text().splitlines()
        if s.strip()
    }
    assert not (repair & normalization), f"{base}: repair and normalization overlap"
    assert not (repair & deleted), f"{base}: repair and delete overlap"
    assert not (normalization & deleted), f"{base}: normalization and delete overlap"

for k in sorted(report):
    print(f"{report[k]:7d}  {k}")
    for e in examples[k]:
        print(f"           e.g. {e}")

for label in report:
    if any(
        term in label
        for term in (
            "IDENTICAL to original",
            "indicators changed",
            "lost from a field",
        )
    ) or ("subfield $" in label and "value changed" in label):
        raise SystemExit(f"Audit failed: {label}: {report[label]}")

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from .config import FIELD_ROLE, IGNORE_TAG_PATTERNS
from .llm import BackendLiteral
from .pairer import pair_values
from .checks.registry import CHECKS
from .normalizers import normalize_by_role
from .missing import is_missing_tracked

OCCURRENCE_TAGS = {"336", "337", "338"}

HEADING_TAGS = {"600", "610", "648", "650", "651", "655"}

UDC_TAGS = {"080"}

TAG_ALIASES = {
    "260": "264",
}

LABEL_ORDER = {
    "IDENTICAL": 0,
    "NON_STANDARDIZED": 1,
    "TYPO": 2,
    "INCOMPLETE": 3,
    "INCORRECT": 4,
    "MISSING": 5,
}

def _gather_occurrences(rec: Dict[str, Any], tag: str) -> List[Dict[str, str]]:
    occs: List[Dict[str, str]] = []
    for f in rec.get("fields", []):
        if not isinstance(f, dict) or tag not in f:
            continue
        payload = f[tag]
        if isinstance(payload, str):
            continue
        occ: Dict[str, str] = {}
        for sf in payload.get("subfields", []):
            k, v = next(iter(sf.items()))
            occ[str(k)] = str(v)
        if occ:
            occs.append(occ)
    return occs

def _udc_key_by_a(occ: Dict[str, str]) -> tuple[str, str]:
    a = occ.get("a", "")
    na = normalize_by_role("udc", a)
    return ("a", na)

def _compare_udc_tag(main_rec: Dict[str, Any], test_rec: Dict[str, Any], role_for) -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []
    A = _gather_occurrences(main_rec, "080")
    B = _gather_occurrences(test_rec, "080")

    idxA: Dict[tuple[str,str], List[Dict[str,str]]] = {}
    for occ in A:
        idxA.setdefault(_udc_key_by_a(occ), []).append(occ)

    idxB: Dict[tuple[str,str], List[Dict[str,str]]] = {}
    for occ in B:
        idxB.setdefault(_udc_key_by_a(occ), []).append(occ)

    visitedB: set[tuple[tuple[str,str], int]] = set()

    for key, listA in idxA.items():
        listB = idxB.get(key, [])
        for k in range(max(len(listA), len(listB))):
            a_occ = listA[k] if k < len(listA) else None
            b_occ = listB[k] if k < len(listB) else None
            if b_occ is not None:
                visitedB.add((key, k))

            if a_occ and b_occ:
                continue

            elif a_occ and not b_occ:
                if not (is_missing_tracked("080", None) or is_missing_tracked("080", "a")):
                    continue
                diffs.append({
                    "tag": "080", "code": None, "role": "udc_occurrence",
                    "value_main": a_occ, "value_test": None,
                    "label": "MISSING", "confidence": 0.9,
                    "details": {"reason": "missing_occurrence_in_test", "missing_tracked": True}
                })

            elif b_occ and not a_occ:
                if not (is_missing_tracked("080", None) or is_missing_tracked("080", "a")):
                    continue
                diffs.append({
                    "tag": "080", "code": None, "role": "udc_occurrence",
                    "value_main": None, "value_test": b_occ,
                    "label": "MISSING", "confidence": 0.9,
                    "details": {"reason": "missing_occurrence_in_main", "missing_tracked": True}
                })

    for key, listB in idxB.items():
        for k, occ in enumerate(listB):
            if (key, k) in visitedB:
                continue
            if not (is_missing_tracked("080", None) or is_missing_tracked("080", "a")):
                continue
            diffs.append({
                "tag": "080", "code": None, "role": "udc_occurrence",
                "value_main": None, "value_test": occ,
                "label": "MISSING", "confidence": 0.9,
                "details": {"reason": "missing_occurrence_in_main", "missing_tracked": True}
            })

    return diffs


def _tag_to_int(tag: str) -> int:
    try:
        return int(tag)
    except Exception:
        return 9999

def _code_rank(code) -> int:
    if code is None:
        return -1
    try:
        return ord(str(code)[0])
    except Exception:
        return 1000



def _diff_sort_key(d: dict):
    return (
        _tag_to_int(d.get("tag", "9999")),
        _code_rank(d.get("code")),
        LABEL_ORDER.get(d.get("label", ""), 99),
        str(d.get("value_main"))[:64],
        str(d.get("value_test"))[:64],
    )


def _heading_key(tag: str, occ: Dict[str, str], role_for) -> tuple[str, str]:
    aid = occ.get("7")
    src = occ.get("2", "")
    a   = occ.get("a", "")
    if aid:
        return ("7", aid)
    na  = normalize_by_role(role_for(tag, "a"), a)
    n2  = normalize_by_role(role_for(tag, "2"), src)
    return ("a2", f"{na}|{n2}")

def _compare_heading_tag(tag: str, main_rec: Dict[str, Any], test_rec: Dict[str, Any], role_for,
                         label_extra="ADDITION", label_missing="MISSING") -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []
    A = _gather_occurrences(main_rec, tag)
    B = _gather_occurrences(test_rec, tag)

    idxA: Dict[tuple[str,str], List[Dict[str,str]]] = {}
    for occ in A:
        idxA.setdefault(_heading_key(tag, occ, role_for), []).append(occ)

    idxB: Dict[tuple[str,str], List[Dict[str,str]]] = {}
    for occ in B:
        idxB.setdefault(_heading_key(tag, occ, role_for), []).append(occ)

    visitedB: set[tuple[tuple[str,str], int]] = set()

    for key, listA in idxA.items():
        listB = idxB.get(key, [])
        for k in range(max(len(listA), len(listB))):
            a_occ = listA[k] if k < len(listA) else None
            b_occ = listB[k] if k < len(listB) else None
            if b_occ is not None:
                visitedB.add((key, k))
            if a_occ and b_occ:
                a_a, b_a = a_occ.get("a",""), b_occ.get("a","")
                a_2, b_2 = a_occ.get("2",""), b_occ.get("2","")
                a_7, b_7 = a_occ.get("7",""), b_occ.get("7","")

                na_a = normalize_by_role(role_for(tag,"a"), a_a)
                nb_a = normalize_by_role(role_for(tag,"a"), b_a)
                na_2 = normalize_by_role(role_for(tag,"2"), a_2)
                nb_2 = normalize_by_role(role_for(tag,"2"), b_2)

                if (a_7 and a_7 == b_7) or (na_2 == nb_2 and na_a == nb_a):
                    continue
                if (a_7 and a_7 == b_7) or (na_2 == nb_2):
                    diffs.append({
                        "tag": tag, "code": None, "role": "heading_occurrence",
                        "value_main": a_occ, "value_test": b_occ,
                        "label": "NON_STANDARDIZED", "confidence": 0.8,
                        "details": {"reason": "same_authority_or_source_different_label"}
                    })
                else:
                    diffs.append({
                        "tag": tag, "code": None, "role": "heading_occurrence",
                        "value_main": a_occ, "value_test": b_occ,
                        "label": "INCORRECT", "confidence": 0.8,
                        "details": {"reason": "different_heading_and_source"}
                    })
            elif a_occ and not b_occ:
                if not (is_missing_tracked(tag, None) or is_missing_tracked(tag, "a")):
                    continue
                diffs.append({
                    "tag": tag, "code": None, "role": "heading_occurrence",
                    "value_main": a_occ, "value_test": None,
                    "label": "MISSING",
                    "confidence": 0.9,
                    "details": {"reason": "missing_heading_in_test", "missing_tracked": True}
                })
            elif b_occ and not a_occ:
                if is_missing_tracked(tag, None) or is_missing_tracked(tag, "a"):
                    diffs.append({
                        "tag": tag, "code": None, "role": "heading_occurrence",
                        "value_main": None, "value_test": b_occ,
                        "label": "MISSING",
                        "confidence": 0.9,
                        "details": {"reason": "missing_heading_in_main", "missing_tracked": True}
                    })
                elif label_extra:
                    diffs.append({
                        "tag": tag, "code": None, "role": "heading_occurrence",
                        "value_main": None, "value_test": b_occ,
                        "label": label_extra,
                        "confidence": 0.8,
                        "details": {"reason": "extra_heading_in_test"}
                    })

    for key, listB in idxB.items():
        for k, occ in enumerate(listB):
            if (key, k) in visitedB:
                continue
            if is_missing_tracked(tag, None) or is_missing_tracked(tag, "a"):
                diffs.append({
                    "tag": tag, "code": None, "role": "heading_occurrence",
                    "value_main": None, "value_test": occ,
                    "label": "MISSING",
                    "confidence": 0.9,
                    "details": {"reason": "missing_heading_in_main", "missing_tracked": True}
                })
            elif label_extra:
                diffs.append({
                    "tag": tag, "code": None, "role": "heading_occurrence",
                    "value_main": None, "value_test": occ,
                    "label": label_extra,
                    "confidence": 0.8,
                    "details": {"reason": "extra_heading_in_test"}
                })
    return diffs

def _normalize_subfields_struct(sfs_raw):
    pairs = []

    if sfs_raw is None:
        return pairs

    if isinstance(sfs_raw, dict):
        for k, v in sfs_raw.items():
            if isinstance(v, list):
                for item in v:
                    pairs.append((str(k), str(item)))
            else:
                pairs.append((str(k), str(v)))
        return pairs

    if isinstance(sfs_raw, (list, tuple)):
        if not sfs_raw:
            return pairs

        if isinstance(sfs_raw[0], dict):
            for sf in sfs_raw:
                if not isinstance(sf, dict):
                    continue
                k, v = next(iter(sf.items()))
                pairs.append((str(k), str(v)))
            return pairs

        if isinstance(sfs_raw[0], (list, tuple)):
            if len(sfs_raw) == 1 and isinstance(sfs_raw[0], (list, tuple)) and len(sfs_raw[0]) > 2:
                sfs_raw = sfs_raw[0]

            if sfs_raw and isinstance(sfs_raw[0], (list, tuple)) and len(sfs_raw[0]) == 2:
                for k, v in sfs_raw:
                    pairs.append((str(k), str(v)))
                return pairs

            flat = list(sfs_raw)
            for i in range(0, len(flat) - 1, 2):
                pairs.append((str(flat[i]), str(flat[i + 1])))
            return pairs

        flat = list(sfs_raw)
        for i in range(0, len(flat) - 1, 2):
            pairs.append((str(flat[i]), str(flat[i + 1])))
        return pairs

    return pairs


def iter_fields(marc_json: Dict[str, Any]):
    for f in marc_json.get("fields", []):
        if not isinstance(f, dict):
            continue
        tag, payload = next(iter(f.items()))

        if isinstance(payload, str):
            yield (tag, None, None, None, payload)
            continue

        ind1 = payload.get("ind1", " ")
        ind2 = payload.get("ind2", " ")
        sfs_raw = payload.get("subfields", [])

        for code, val in _normalize_subfields_struct(sfs_raw):
            yield (tag, ind1, ind2, code, val)


def _record_key(rec: Dict[str, Any]) -> Optional[str]:
    for f in rec.get("fields", []):
        if isinstance(f, dict) and "001" in f:
            return f["001"]
    return None


def _match_tag_pattern(tag: str, pattern: str) -> bool:
    pattern = str(pattern or "").strip().upper()
    if not pattern:
        return False
    tag = str(tag or "").upper()
    if len(pattern) == len(tag) == 3:
        return all(
            (pc == "X" or pc == tc)
            for tc, pc in zip(tag, pattern)
        )
    return tag == pattern


def _is_tag_ignored(tag: str) -> bool:
    return any(_match_tag_pattern(tag, pat) for pat in IGNORE_TAG_PATTERNS)


def _canonical_tag(tag: str) -> str:
    return TAG_ALIASES.get(str(tag), str(tag))


def _role_for(tag: str, code: Optional[str]) -> str:
    return FIELD_ROLE.get((tag, code), "generic")


def _build_map(rec: Dict[str, Any]):

    mp: Dict[str, Dict[Optional[str], List[str]]] = {}
    for tag, _i1, _i2, code, val in iter_fields(rec):
        tag = _canonical_tag(tag)
        mp.setdefault(tag, {}).setdefault(code, []).append(val)
    return mp


def _classify(a: str, b: str, role: str, context: Optional[Dict[str, Any]] = None):
    for check in CHECKS:
        res = check(a, b, role, context)
        if res is not None:
            return res
    return {"label": "INCORRECT", "confidence": 0.8, "details": {}}



def _occ_key(tag: str, occ: Dict[str, str], role_for) -> Tuple[str, str]:
    b, a, two = occ.get("b"), occ.get("a"), occ.get("2", "")
    if b:
        nb = normalize_by_role(role_for(tag, "b"), b)
        n2 = normalize_by_role(role_for(tag, "2"), two)
        return ("b", f"{nb}|{n2}")
    if a:
        na = normalize_by_role(role_for(tag, "a"), a)
        n2 = normalize_by_role(role_for(tag, "2"), two)
        return ("a", f"{na}|{n2}")
    return ("z", json.dumps(occ, ensure_ascii=False))


def _compare_occurrence_tag(tag: str, main_rec: Dict[str, Any], test_rec: Dict[str, Any], role_for):
    diffs: List[Dict[str, Any]] = []
    A = _gather_occurrences(main_rec, tag)
    B = _gather_occurrences(test_rec, tag)

    idxA: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for occ in A:
        idxA.setdefault(_occ_key(tag, occ, role_for), []).append(occ)

    idxB: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for occ in B:
        idxB.setdefault(_occ_key(tag, occ, role_for), []).append(occ)

    visitedB: set[Tuple[Tuple[str, str], int]] = set()

    for key, listA in idxA.items():
        listB = idxB.get(key, [])
        for k in range(max(len(listA), len(listB))):
            a_occ = listA[k] if k < len(listA) else None
            b_occ = listB[k] if k < len(listB) else None
            if b_occ is not None:
                visitedB.add((key, k))

            if a_occ is not None and b_occ is not None:
                a_a, b_a = a_occ.get("a", ""), b_occ.get("a", "")
                a_b, b_b = a_occ.get("b", ""), b_occ.get("b", "")
                a_2, b_2 = a_occ.get("2", ""), b_occ.get("2", "")

                na_a = normalize_by_role(role_for(tag, "a"), a_a)
                nb_a = normalize_by_role(role_for(tag, "a"), b_a)
                na_b = normalize_by_role(role_for(tag, "b"), a_b)
                nb_b = normalize_by_role(role_for(tag, "b"), b_b)
                na_2 = normalize_by_role(role_for(tag, "2"), a_2)
                nb_2 = normalize_by_role(role_for(tag, "2"), b_2)

                if na_b == nb_b and na_2 == nb_2 and na_a != nb_a:
                    diffs.append({
                        "tag": tag, "code": None, "role": "rda_content_occurrence",
                        "value_main": a_occ, "value_test": b_occ,
                        "label": "NON_STANDARDIZED", "confidence": 0.8,
                        "details": {"reason": "same_code_same_source_different_term"}
                    })
            elif a_occ is not None and b_occ is None:
                if not (is_missing_tracked(tag, None) or is_missing_tracked(tag, "a")):
                    continue
                diffs.append({
                    "tag": tag, "code": None, "role": "rda_content_occurrence",
                    "value_main": a_occ, "value_test": None,
                    "label": "MISSING", "confidence": 0.9,
                    "details": {"reason": "missing_occurrence_in_test", "missing_tracked": True}
                })
            elif a_occ is None and b_occ is not None:
                if not (is_missing_tracked(tag, None) or is_missing_tracked(tag, "a")):
                    continue
                diffs.append({
                    "tag": tag, "code": None, "role": "rda_content_occurrence",
                    "value_main": None, "value_test": b_occ,
                    "label": "MISSING", "confidence": 0.9,
                    "details": {"reason": "missing_occurrence_in_main", "missing_tracked": True}
                })

    for key, listB in idxB.items():
        for k, occ in enumerate(listB):
            if (key, k) in visitedB:
                continue
            if not (is_missing_tracked(tag, None) or is_missing_tracked(tag, "a")):
                continue
            diffs.append({
                "tag": tag, "code": None, "role": "rda_content_occurrence",
                "value_main": None, "value_test": occ,
                "label": "MISSING", "confidence": 0.9,
                "details": {"reason": "missing_occurrence_in_main", "missing_tracked": True}
            })

    return diffs


def compare_records(
    main_rec: Dict[str, Any],
    test_rec: Dict[str, Any],
    *,
    include_identical: bool = False,
    nonstandard_llm: bool = False,
    llm_backend: Optional[BackendLiteral] = None,
    llm_enabled: bool = True,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "main_key": _record_key(main_rec),
        "test_key": _record_key(test_rec),
        "differences": [],
    }
    if include_identical:
        result["identical"] = []

    A = _build_map(main_rec)
    B = _build_map(test_rec)

    tags_present = set(A.keys()) | set(B.keys())
    usable_tags = {tag for tag in tags_present if not _is_tag_ignored(tag)}

    present_udc = usable_tags & UDC_TAGS
    for _ in present_udc:
        result["differences"].extend(_compare_udc_tag(main_rec, test_rec, _role_for))

    present_special = usable_tags & OCCURRENCE_TAGS
    for tag in sorted(present_special):
        for d in _compare_occurrence_tag(tag, main_rec, test_rec, _role_for):
            result["differences"].append(d)

    present_headings = usable_tags & HEADING_TAGS
    for tag in sorted(present_headings):
        result["differences"].extend(_compare_heading_tag(tag, main_rec, test_rec, _role_for, label_extra=None))

    skip = UDC_TAGS | OCCURRENCE_TAGS | HEADING_TAGS
    all_tags = sorted(usable_tags - skip)   

    total_compared = 0
    llm_allowed = bool(llm_enabled)
    use_nonstandard_llm = bool(nonstandard_llm) and llm_allowed
    classify_context: Dict[str, Any] = {
        "nonstandard_llm": use_nonstandard_llm,
        "allow_llm": llm_allowed,
    }
    if llm_allowed and llm_backend is not None:
        classify_context["llm_backend"] = llm_backend

    for tag in all_tags:
        codes = set((A.get(tag) or {}).keys()) | set((B.get(tag) or {}).keys())
        for code in sorted(codes, key=lambda c: (c is None, c or "")):
            valsA = A.get(tag, {}).get(code, [])
            valsB = B.get(tag, {}).get(code, [])
            role = _role_for(tag, code)

            pairs = pair_values(valsA, valsB, role)

            for i, j in pairs:
                va = valsA[i] if i is not None else None
                vb = valsB[j] if j is not None else None

                if va is not None and vb is not None:
                    total_compared += 1
                    res = _classify(str(va), str(vb), role, classify_context)
                    if res["label"] != "IDENTICAL":
                        result["differences"].append({
                            "tag": tag, "code": code, "role": role,
                            "value_main": va, "value_test": vb,
                            **res
                        })
                    elif include_identical:
                        result["identical"].append({
                            "tag": tag, "code": code, "role": role,
                            "value_main": va, "value_test": vb,
                            **res
                        })

                elif va is not None and vb is None:
                    if not is_missing_tracked(tag, code):
                        continue
                    result["differences"].append({
                        "tag": tag, "code": code, "role": role,
                        "value_main": va, "value_test": None,
                        "label": "MISSING", "confidence": 0.9,
                        "details": {"reason": "missing_in_test", "missing_tracked": True}
                    })

                elif va is None and vb is not None:
                    if not is_missing_tracked(tag, code):
                        continue
                    result["differences"].append({
                        "tag": tag, "code": code, "role": role,
                        "value_main": None, "value_test": vb,
                        "label": "MISSING", "confidence": 0.9,
                        "details": {"reason": "missing_in_main", "missing_tracked": True}
                    })

    result["differences"].sort(key=_diff_sort_key)
    if include_identical and "identical" in result:
        result["identical"].sort(key=_diff_sort_key)

    result["stats"] = {
        "tags_in_main": len(A),
        "tags_in_test": len(B),
        "paired_value_comparisons": total_compared,
        "differences_found": len(result["differences"]),
    }
    return result

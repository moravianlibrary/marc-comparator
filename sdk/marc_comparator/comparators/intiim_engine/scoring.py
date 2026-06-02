from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from .config import AGG_P, AGGREGATION, HINGE_ACCEL_ENABLED, HINGE_EXP, HINGE_POINT, RECORD_CAP
from .marc21_quality import DEFAULT_WEIGHTS

LABEL_TO_CATEGORY = {
    "TYPO": "typo",
    "INCORRECT": "wrong-value",
    "INCOMPLETE": "incomplete-value",
    "NON_STANDARDIZED": "non-standard-content",
    "ADDITION": "addition",
    "REMOVED": "incomplete-value",
    "MISSING": "wrong-value",
}

EXTRA_REASONS = {
    "extra_in_test",
    "extra_heading_in_test",
    "extra_occurrence_in_test",
    "auxiliary_added",
}
MISSING_REASONS = {
    "missing_in_test",
    "missing_in_main",
    "missing_heading_in_test",
    "missing_heading_in_main",
    "missing_occurrence_in_test",
    "missing_occurrence_in_main",
}


def _load_weights(path: str | None = None) -> dict[str, int]:
    p = path or os.environ.get("MARC_WEIGHTS_PATH")

    if p:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        raw = data.get("responses", {})
    else:
        raw = DEFAULT_WEIGHTS.get("responses", {})

    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[k] = int(v) if v not in ("", None) else 0
        except Exception:
            out[k] = 0
    return out


def _category_for_diff(diff: dict[str, Any]) -> str:
    details = diff.get("details") or {}
    reason = details.get("reason", "")
    if diff.get("label") == "MISSING":
        if details.get("missing_tracked"):
            return "wrong-value"
        return "incomplete-value"
    if reason in MISSING_REASONS:
        return "incomplete-value"
    if reason in EXTRA_REASONS:
        return "addition"
    return LABEL_TO_CATEGORY.get(diff.get("label", "INCORRECT"), "wrong-value")


def _weight_key(tag: str, code: str | None, category: str) -> tuple[str, ...]:
    keys = []
    if code:
        keys.append(f"field_{tag}_{code}_{category}")
    keys.append(f"field_{tag}_{category}")
    return tuple(keys)


def _pick_weight(
    weights: dict[str, int], tag: str, code: str | None, category: str, default: int = 1
) -> int:
    for k in _weight_key(tag, code, category):
        if k in weights:
            return int(weights[k])
    return default


def _field_overall_cap(weights: dict[str, int], tag: str) -> int | None:
    k = f"field_{tag}_overall"
    return int(weights[k]) if k in weights and weights[k] > 0 else None


def _field_max_weight(weights: dict[str, int], tag: str) -> int:
    prefix = f"field_{tag}_"
    max_w = 0
    for k, v in weights.items():
        if not k.startswith(prefix):
            continue
        if k == f"field_{tag}_overall":
            continue
        try:
            max_w = max(max_w, int(v))
        except Exception:
            pass
    return max_w if max_w > 0 else 1


def _lp_norm(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return max(values)
    return (sum((abs(v) ** p) for v in values)) ** (1.0 / p)


def _hinge_accelerate(x: float, *, hinge: float, cap: float, exp: float) -> float:
    if x <= hinge:
        return x
    span = max(1e-9, cap - hinge)
    k = span ** (1.0 - exp)
    return hinge + k * (x - hinge) ** exp


def score_differences(
    differences: list[dict[str, Any]], *, weights_path: str | None = None
) -> dict[str, Any]:
    weights = _load_weights(weights_path)

    by_tag: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    components: list[dict[str, Any]] = []

    for d in differences:
        tag = str(d.get("tag", ""))
        code = d.get("code")
        if isinstance(code, (list, dict)):
            code = None
        if code is not None:
            code = str(code)

        category = _category_for_diff(d)
        w = _pick_weight(weights, tag, code, category, default=1)

        entry = {
            "tag": tag,
            "code": code,
            "label": d.get("label"),
            "category": category,
            "weight": w,
            "reason": (d.get("details") or {}).get("reason"),
            "role": d.get("role"),
            "value_main": d.get("value_main"),
            "value_test": d.get("value_test"),
        }
        components.append(entry)
        by_tag[tag].append(entry)

    contributions: list[dict[str, Any]] = []
    applied_values: list[float] = []

    for tag, entries in sorted(by_tag.items()):
        cap = _field_overall_cap(weights, tag)
        max_w = _field_max_weight(weights, tag)
        tag_cap = float(cap if cap is not None else max_w)

        proportional_sum = 0.0
        for e in entries:
            proportional_sum += tag_cap * (float(e["weight"]) / float(max_w))

        applied = min(proportional_sum, tag_cap)
        applied_values.append(applied)

        contributions.append(
            {
                "tag": tag,
                "cap": tag_cap if cap is not None else None,
                "max_weight": max_w,
                "proportional_sum": round(proportional_sum, 4),
                "applied": round(applied, 4),
                "count": len(entries),
            }
        )

    p = float(AGG_P) if AGGREGATION == "lpnorm" else 2.0
    base = _lp_norm(applied_values, p)
    accelerated = (
        _hinge_accelerate(
            base, hinge=float(HINGE_POINT), cap=float(RECORD_CAP), exp=float(HINGE_EXP)
        )
        if HINGE_ACCEL_ENABLED
        else base
    )
    record_exact = min(float(RECORD_CAP), accelerated)

    return {
        "record_score_30": int(round(record_exact)),
        "record_score_30_exact": round(record_exact, 4),
        "aggregation": {
            "method": "lpnorm+hinge" if HINGE_ACCEL_ENABLED else "lpnorm",
            "p": p,
            "record_cap": RECORD_CAP,
            "hinge_point": HINGE_POINT if HINGE_ACCEL_ENABLED else None,
            "hinge_exp": HINGE_EXP if HINGE_ACCEL_ENABLED else None,
        },
        "field_contributions": contributions,
        "components": components,
    }

from __future__ import annotations

import os
from typing import Any

from .llm import BackendLiteral, verify_label

LLM_VERIFY_ENABLED = os.getenv("LLM_VERIFY_ENABLED", "true").lower() == "true"
LLM_OVERRIDE_LABELS = os.getenv("LLM_OVERRIDE_LABELS", "false").lower() == "true"
LLM_TAG_ALLOW = set(x.strip() for x in os.getenv("LLM_TAG_ALLOW", "").split(",") if x.strip())
LLM_TAG_DENY = set(x.strip() for x in os.getenv("LLM_TAG_DENY", "").split(",") if x.strip())

_PRESENCE_REASONS = {
    "missing_in_test",
    "missing_heading_in_test",
    "missing_occurrence_in_test",
    "extra_in_test",
    "extra_heading_in_test",
    "extra_occurrence_in_test",
    "auxiliary_added",
}


def _should_verify(tag: str) -> bool:
    if LLM_TAG_ALLOW:
        return tag in LLM_TAG_ALLOW
    if LLM_TAG_DENY:
        return tag not in LLM_TAG_DENY
    return True


def _presence_only(d: dict[str, Any]) -> bool:
    if d.get("value_main") is None or d.get("value_test") is None:
        return True
    reason = (d.get("details") or {}).get("reason", "")
    return reason in _PRESENCE_REASONS


def _stringify_occ(occ: Any) -> str | None:
    if occ is None:
        return None
    if isinstance(occ, str):
        return occ
    if isinstance(occ, dict):
        order = list("abcdefghijklmnopqrstuvwxyz") + [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        ]
        items = sorted(
            occ.items(), key=lambda kv: (order.index(kv[0]) if kv[0] in order else 999, kv[0])
        )
        parts = []
        for k, v in items:
            parts.append(f"${k} {v}")
        return " ".join(parts)
    return None


def apply_llm_verification(
    differences: list[dict[str, Any]], *, backend: BackendLiteral | None = None
) -> list[dict[str, Any]]:
    if not LLM_VERIFY_ENABLED:
        return differences

    out: list[dict[str, Any]] = []
    for d in differences:
        lbl = d.get("label")
        tag = str(d.get("tag", ""))
        if lbl == "IDENTICAL" or not _should_verify(tag) or _presence_only(d):
            out.append(d)
            continue

        role = str(d.get("role", "generic"))
        code = d.get("code")
        code = None if isinstance(code, (list, dict)) else (str(code) if code is not None else None)

        fieldA = _stringify_occ(d.get("value_main"))
        fieldB = _stringify_occ(d.get("value_test"))

        a = str(d.get("value_main")) if isinstance(d.get("value_main"), str) else ""
        b = str(d.get("value_test")) if isinstance(d.get("value_test"), str) else ""

        review = verify_label(
            a, b, role, lbl, tag, code, fieldA=fieldA, fieldB=fieldB, backend=backend
        )
        dd = dict(d)
        dd["llm_review"] = review

        agreed = review.get("agreed")
        suggested = review.get("suggested")
        if LLM_OVERRIDE_LABELS and (agreed is False) and suggested and suggested != lbl:
            dd["details"] = dict(dd.get("details") or {})
            dd["details"]["reason"] = "llm_override"
            dd["label"] = suggested

        out.append(dd)
    return out

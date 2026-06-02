from __future__ import annotations

from typing import Any

from ..normalizers import normalize_by_role
from ..token_metrics import jaccard
from ._parts import PART_SENSITIVE_ROLES, differs_only_by_part_tokens


def _is_incomplete(na: str, nb: str) -> bool:
    if not na or not nb:
        return False

    def _covered(shorter: str, longer: str) -> bool:
        if not shorter or shorter == longer:
            return False
        start = longer.find(shorter)
        while start != -1:
            before_ok = (start == 0) or not longer[start - 1].isalnum()
            end = start + len(shorter)
            after_ok = (end >= len(longer)) or not longer[end].isalnum()
            if before_ok and after_ok:
                return True
            start = longer.find(shorter, start + 1)
        return False

    if _covered(na, nb) or _covered(nb, na):
        return True

    sa = set(na.split())
    sb = set(nb.split())
    return bool(sa) and (sa.issubset(sb) or sb.issubset(sa))


def run(a: str, b: str, role: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    na, nb = normalize_by_role(role, a), normalize_by_role(role, b)
    if role in PART_SENSITIVE_ROLES and differs_only_by_part_tokens(na, nb):
        return None
    if _is_incomplete(na, nb):
        jac = jaccard(na, nb)
        if jac == 0.0:
            return None
        conf = 0.8 if jac >= 0.9 else 0.65
        return {"label": "INCOMPLETE", "confidence": conf, "details": {"jaccard": jac}}
    return None

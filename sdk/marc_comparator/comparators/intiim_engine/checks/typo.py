from __future__ import annotations
from typing import Optional, Dict, Any

from ..normalizers import normalize_by_role
from ..token_metrics import similarity, jaccard
from ..config import SIM_HIGH, SIM_MED, TOKEN_JACCARD_MED, ASK_LLM_IF_UNSURE
from ..llm import verify_label
from ._parts import PART_SENSITIVE_ROLES, differs_only_by_part_tokens


def damerau_levenshtein(a: str, b: str) -> int:
    d, la, lb = {}, len(a), len(b)
    for i in range(-1, la+1): d[(i, -1)] = i + 1
    for j in range(-1, lb+1): d[(-1, j)] = j + 1
    for i in range(la):
        for j in range(lb):
            cost = 0 if a[i] == b[j] else 1
            d[(i, j)] = min(
                d[(i-1, j)] + 1, d[(i, j-1)] + 1, d[(i-1, j-1)] + cost
            )
            if i and j and a[i] == b[j-1] and a[i-1] == b[j]:
                d[(i, j)] = min(d[(i, j)], d[(i-2, j-2)] + 1)
    return d[(la-1, lb-1)]

def run(a: str, b: str, role: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if role.startswith("control_"):
        return None

    na, nb = normalize_by_role(role, a), normalize_by_role(role, b)
    sim = similarity(na, nb)
    jac = jaccard(na, nb)
    allow_llm = bool((context or {}).get("allow_llm", True))

    if role in PART_SENSITIVE_ROLES and differs_only_by_part_tokens(na, nb):
        return None

    if sim >= SIM_HIGH:
        return {"label": "TYPO", "confidence": 0.8, "details": {"sim": sim, "jaccard": jac}}

    if SIM_MED <= sim < SIM_HIGH and jac >= TOKEN_JACCARD_MED:
        if ASK_LLM_IF_UNSURE and allow_llm:
            try:
                backend = (context or {}).get("llm_backend") if context else None
                review = verify_label(a, b, role, label="TYPO", tag="(n/a)", code=None, backend=backend)
                agreed = review.get("agreed")
                suggested = review.get("suggested")

                if agreed is True:
                    return {
                        "label": "TYPO",
                        "confidence": 0.75,
                        "details": {"sim": sim, "jaccard": jac, "llm": "confirmed", "llm_raw": review.get("raw")},
                    }

                if suggested == "TYPO":
                    return {
                        "label": "TYPO",
                        "confidence": 0.7,
                        "details": {"sim": sim, "jaccard": jac, "llm": "suggested", "llm_raw": review.get("raw")},
                    }

                return None

            except Exception:
                return {"label": "TYPO", "confidence": 0.6, "details": {"sim": sim, "jaccard": jac, "llm": "error"}}

        return {"label": "TYPO", "confidence": 0.6, "details": {"sim": sim, "jaccard": jac}}

    return None

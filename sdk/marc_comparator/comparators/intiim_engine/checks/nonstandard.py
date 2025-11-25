from __future__ import annotations
from typing import Optional, Dict, Any

from ..normalizers import normalize_by_role, norm_generic
from ..llm import ask_same_written_differently
from ._parts import PART_SENSITIVE_ROLES, differs_only_by_part_tokens

def _strip_punct_space(s: str) -> str:
    if not s:
        return ""
    return "".join(ch for ch in s if ch.isalnum()).lower()

def _heuristic_nonstandard(
    a: str,
    b: str,
    role: str,
    na: Optional[str] = None,
    nb: Optional[str] = None,
) -> bool:
    if not a or not b or a == b:
        return False

    if na is None:
        na = normalize_by_role(role, a)
    if nb is None:
        nb = normalize_by_role(role, b)
    if na and nb and na == nb:
        return True

    if _strip_punct_space(a) == _strip_punct_space(b):
        return True

    if norm_generic(a) == norm_generic(b):
        return True

    return False

def run(a: str, b: str, role: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    na = normalize_by_role(role, a)
    nb = normalize_by_role(role, b)
    if role in PART_SENSITIVE_ROLES and differs_only_by_part_tokens(na, nb):
        return None

    if _heuristic_nonstandard(a, b, role, na, nb):
        return {
            "label": "NON_STANDARDIZED",
            "confidence": 0.8,
            "details": {"reason": "heuristic_match"}
        }

    allow_llm = bool((context or {}).get("allow_llm", True))
    use_llm = allow_llm and bool((context or {}).get("nonstandard_llm"))
    if use_llm:
        backend = (context or {}).get("llm_backend")
        review = ask_same_written_differently(a, b, role, tag="(n/a)", code=None, backend=backend)
        if review.get("answer") is True:
            return {
                "label": "NON_STANDARDIZED",
                "confidence": 0.7,
                "details": {"reason": "llm_same_written_differently", "llm_raw": review.get("raw")}
            }

    return None

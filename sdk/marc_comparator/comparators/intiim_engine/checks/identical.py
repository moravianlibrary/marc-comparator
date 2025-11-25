from __future__ import annotations
from typing import Optional, Dict, Any
from ..normalizers import normalize_by_role

def run(a: str, b: str, role: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    na, nb = normalize_by_role(role, a), normalize_by_role(role, b)
    if na == nb:
        return {"label": "IDENTICAL", "confidence": 1.0, "details": {"norm_a": na, "norm_b": nb}}
    return None

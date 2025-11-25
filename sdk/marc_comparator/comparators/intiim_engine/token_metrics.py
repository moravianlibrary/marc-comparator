from __future__ import annotations
import re
from rapidfuzz import fuzz

def token_set(s: str) -> set[str]:
    return set(t for t in re.split(r"[^\w]+", s) if t)

def similarity(a: str, b: str) -> float:
    return float(fuzz.ratio(a, b))

def jaccard(a: str, b: str) -> float:
    ta, tb = token_set(a), token_set(b)
    if not ta and not tb: return 1.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0

from __future__ import annotations
from typing import List, Tuple, Optional, Set
from .normalizers import normalize_by_role
from .token_metrics import similarity, jaccard

def pair_values(vals_a: List[str], vals_b: List[str], role: str) -> List[Tuple[Optional[int], Optional[int]]]:
    used_b: Set[int] = set()
    pairs: List[Tuple[Optional[int], Optional[int]]] = []
    for i, va in enumerate(vals_a):
        na = normalize_by_role(role, str(va))
        best_j, best_score = None, -1.0
        for j, vb in enumerate(vals_b):
            if j in used_b: continue
            nb = normalize_by_role(role, str(vb))
            score = (similarity(na, nb) + 100.0 * jaccard(na, nb)) / 2.0
            if score > best_score:
                best_score, best_j = score, j
        if best_j is not None:
            used_b.add(best_j)
            pairs.append((i, best_j))
        else:
            pairs.append((i, None))
    for j in range(len(vals_b)):
        if j not in used_b:
            pairs.append((None, j))
    return pairs

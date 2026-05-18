from __future__ import annotations
from typing import List, Tuple, Optional, Set
from .normalizers import normalize_by_role
from .token_metrics import similarity, jaccard

def pair_values(vals_a: List[str], vals_b: List[str], role: str) -> List[Tuple[Optional[int], Optional[int]]]:
    # Pre-compute all pairwise scores
    norms_a = [normalize_by_role(role, str(va)) for va in vals_a]
    norms_b = [normalize_by_role(role, str(vb)) for vb in vals_b]

    candidates: List[Tuple[float, int, int]] = []
    for i, na in enumerate(norms_a):
        for j, nb in enumerate(norms_b):
            score = (similarity(na, nb) + 100.0 * jaccard(na, nb)) / 2.0
            candidates.append((score, i, j))

    # Sort descending by score so best matches are assigned first
    candidates.sort(key=lambda x: -x[0])

    used_a: Set[int] = set()
    used_b: Set[int] = set()
    pairs: List[Tuple[Optional[int], Optional[int]]] = []

    for _score, i, j in candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        pairs.append((i, j))

    # Unmatched A values
    for i in range(len(vals_a)):
        if i not in used_a:
            pairs.append((i, None))

    # Unmatched B values
    for j in range(len(vals_b)):
        if j not in used_b:
            pairs.append((None, j))

    return pairs

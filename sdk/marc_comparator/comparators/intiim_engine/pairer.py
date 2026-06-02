from __future__ import annotations

from .normalizers import normalize_by_role
from .token_metrics import jaccard, similarity


def pair_values(
    vals_a: list[str], vals_b: list[str], role: str
) -> list[tuple[int | None, int | None]]:
    # Pre-compute all pairwise scores
    norms_a = [normalize_by_role(role, str(va)) for va in vals_a]
    norms_b = [normalize_by_role(role, str(vb)) for vb in vals_b]

    candidates: list[tuple[float, int, int]] = []
    for i, na in enumerate(norms_a):
        for j, nb in enumerate(norms_b):
            score = (similarity(na, nb) + 100.0 * jaccard(na, nb)) / 2.0
            candidates.append((score, i, j))

    # Sort descending by score so best matches are assigned first
    candidates.sort(key=lambda x: -x[0])

    used_a: set[int] = set()
    used_b: set[int] = set()
    pairs: list[tuple[int | None, int | None]] = []

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

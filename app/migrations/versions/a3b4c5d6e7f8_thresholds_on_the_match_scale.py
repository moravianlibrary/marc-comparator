"""move stored score thresholds onto the 0-15 match scale

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-30 15:20:00.000000

The defaults moved with the scale, but a saved settings row keeps whatever it
was saved with, and those values are read back as if they were match scores.
Left alone, a stored `excellent_threshold` of 6 — the old penalty, out of 30 —
reads as 6 out of 15, which puts every comparison above 6 in the Excellent
band and makes Moderate unreachable, because it now sits *below* Excellent.
Verified on the local catalogue: 45,409 of 47,777 comparisons came back
Excellent and not one came back Moderate.

Each threshold is converted by the map its own old scale implies, so a value
somebody chose deliberately keeps its meaning:

  * the comparator's two thresholds were penalties out of 30, so
    `match = 15 - penalty / 2` — the same map the scores themselves took, and
    the old defaults 6 and 12 come out as 12 and 9.

  * every linker floor and `confident_threshold` was a normalized 0-1 score,
    so the old piecewise curve is inverted and then re-expressed. Its three
    segments are exact, being linear: 0.9 lands on 12.0 and 0.7 on 9.0.

  * `candidate_margin` is a *difference* between two 0-1 scores, which has no
    exact inverse — the curve it lived on is not linear across its whole
    range. Near the top, where the margin is applied, 0.05 spans three points
    of penalty, so it becomes 1.5. That is a re-reading of a guess, and it is
    documented as a guess where it is defined.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MATCH_SCALE_MAX = 15.0
RECORD_CAP = 30.0

#: The old `normalize_score` curve, as (penalty, normalized score) knots.
_KNOTS = ((0.0, 1.0), (6.0, 0.9), (12.0, 0.7), (RECORD_CAP, 0.0))

#: The scopes, spelled as the database holds them. SQLAlchemy persists a
#: StrEnum's member *names*, so `SettingsScope.Comparison` is stored as
#: "Comparison" and not as its value, "comparators".
_COMPARISON = "Comparison"
_LINKING = "AuthorityLinking"

#: Where a comparator threshold lives. Its old value was a penalty out of 30.
_PENALTY_KEYS = (
    (_COMPARISON, ("comparator", "excellent_threshold")),
    (_COMPARISON, ("comparator", "moderate_threshold")),
)

#: Where a 0-1 score threshold lives.
_SCORE_KEYS = (
    (_LINKING, ("confident_threshold",)),
    (_LINKING, ("knihovny-cz", "minimum_confidence")),
    (_LINKING, ("marcxml-dump", "identifier_minimum_confidence")),
    (_LINKING, ("marcxml-dump", "title_minimum_confidence")),
)

#: A difference between two 0-1 scores, not a score.
_MARGIN_KEYS = ((_LINKING, ("candidate_margin",)),)

#: What 0.05 of the old curve is worth near the top of it, in match points.
_MARGIN_AT_THE_TOP = 1.5 / 0.05


def _match_from_penalty(penalty: float) -> float:
    return MATCH_SCALE_MAX - penalty / 2.0


def _penalty_from_score(score: float) -> float:
    """Invert the old piecewise-linear normalization.

    Exact, because every segment is linear. Out-of-range input is clamped
    rather than extrapolated: a stored value outside 0-1 was never a score
    this curve produced.
    """

    score = max(0.0, min(1.0, score))
    for (p_lo, s_lo), (p_hi, s_hi) in zip(_KNOTS, _KNOTS[1:], strict=False):
        if s_hi <= score <= s_lo:
            if s_lo == s_hi:
                return p_lo
            return p_lo + (p_hi - p_lo) * (s_lo - score) / (s_lo - s_hi)
    return RECORD_CAP


def _convert(data: dict, path: tuple[str, ...], convert) -> bool:
    """Rewrite one value in place, reporting whether anything changed."""
    node = data
    for key in path[:-1]:
        node = node.get(key) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return False

    old = node.get(path[-1])
    if not isinstance(old, (int, float)) or isinstance(old, bool):
        return False

    new = round(convert(float(old)), 4)
    if new == old:
        return False

    node[path[-1]] = new
    return True


def _rewrite(forward: bool) -> None:
    settings = sa.table(
        "settings",
        sa.column("scope", sa.String),
        sa.column("data", JSONB),
    )
    connection = op.get_bind()
    rows = connection.execute(sa.select(settings.c.scope, settings.c.data)).all()

    if forward:
        penalty = _match_from_penalty
        score = lambda value: _match_from_penalty(_penalty_from_score(value))  # noqa: E731
        margin = lambda value: value * _MARGIN_AT_THE_TOP  # noqa: E731
    else:
        penalty = lambda value: (MATCH_SCALE_MAX - value) * 2.0  # noqa: E731

        def score(value: float) -> float:
            """Back onto 0-1, by walking the same knots the other way."""
            target = (MATCH_SCALE_MAX - value) * 2.0
            for (p_lo, s_lo), (p_hi, s_hi) in zip(_KNOTS, _KNOTS[1:], strict=False):
                if p_lo <= target <= p_hi:
                    if p_hi == p_lo:
                        return s_lo
                    return s_lo + (s_hi - s_lo) * (target - p_lo) / (p_hi - p_lo)
            return 0.0

        margin = lambda value: value / _MARGIN_AT_THE_TOP  # noqa: E731

    for scope, data in rows:
        if not isinstance(data, dict):
            continue

        changed = False
        for owner, path in _PENALTY_KEYS:
            if scope == owner:
                changed |= _convert(data, path, penalty)
        for owner, path in _SCORE_KEYS:
            if scope == owner:
                changed |= _convert(data, path, score)
        for owner, path in _MARGIN_KEYS:
            if scope == owner:
                changed |= _convert(data, path, margin)

        if changed:
            connection.execute(settings.update().where(settings.c.scope == scope).values(data=data))


def upgrade() -> None:
    _rewrite(forward=True)


def downgrade() -> None:
    _rewrite(forward=False)

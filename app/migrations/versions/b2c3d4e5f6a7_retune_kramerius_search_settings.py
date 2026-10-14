"""drop the retired kramerius-links URL settings and split its timeout

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-14 10:00:00.000000

Stored settings win over the model's defaults, so a field removed from the
model leaves a dead key behind and a default that *changed* never takes
effect at all. Both had happened here: the saved config still carried
`url_to_pid_pattern` and its two companions, and its `own_host_pattern` was
the version from before the lookalike-host guard — so the deployed validator
was still matching `kramerius.mzk.cz.example.com` as one of ours.

`search_timeout` becomes `harvest_timeout`. The stored 180 was chosen for a
harvest page of a thousand documents and is right for that; it was only ever
wrong as the wait for a single PID, which now has `lookup_timeout` and its
own much shorter default.

A value that has been edited away from the old shipped default is left alone
and logged. Overwriting a setting somebody deliberately changed is worse than
leaving it stale, and nothing here is load-bearing enough to justify it.
"""

import json
import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")

VALIDATOR = "kramerius-links"

#: Settings the model no longer has. Two were folded into one another and the
#: third is now expressed as a path rather than a whole URL.
RETIRED = (
    "url_to_pid_pattern",
    "url_to_pid_wrong_path_pattern",
    "url_to_pid_fallback_pattern",
)

#: Only replaced when the stored value is still exactly what shipped.
OLD_OWN_HOST = r"^https?://(?:www\.)?(?:digitalniknihovna\.cz/mzk|kramerius\.mzk\.cz)"
NEW_OWN_HOST = r"^https?://(?:www\.)?(?:digitalniknihovna\.cz/mzk|kramerius\.mzk\.cz)(?=[/?#]|$)"


def _edit(upgrade: bool) -> None:
    connection = op.get_bind()
    row = connection.execute(
        text("SELECT data FROM settings WHERE scope = 'Validation'")
    ).scalar_one_or_none()
    if row is None:
        return

    data = json.loads(row) if isinstance(row, str) else dict(row)
    config = dict(data.get(VALIDATOR) or {})
    if not config:
        return

    if upgrade:
        for key in RETIRED:
            config.pop(key, None)

        stored_host = config.get("own_host_pattern")
        if stored_host == OLD_OWN_HOST:
            config["own_host_pattern"] = NEW_OWN_HOST
        elif stored_host not in (None, NEW_OWN_HOST):
            logger.warning(
                "own_host_pattern has been edited away from the shipped default; "
                "leaving it as it is. Without the trailing (?=[/?#]|$) a host that "
                "merely starts with ours, such as kramerius.mzk.cz.example.com, is "
                "read as our own digital library."
            )

        if "search_timeout" in config:
            config.setdefault("harvest_timeout", config.pop("search_timeout"))
            config.pop("search_timeout", None)
    else:
        if config.get("own_host_pattern") == NEW_OWN_HOST:
            config["own_host_pattern"] = OLD_OWN_HOST
        if "harvest_timeout" in config:
            config.setdefault("search_timeout", config.pop("harvest_timeout"))
            config.pop("harvest_timeout", None)
        config.pop("canonical_path_pattern", None)
        config.pop("non_canonical_path_pattern", None)
        config.pop("lookup_timeout", None)

    data[VALIDATOR] = config
    connection.execute(
        text("UPDATE settings SET data = :data WHERE scope = 'Validation'"),
        {"data": json.dumps(data, ensure_ascii=False)},
    )


def upgrade() -> None:
    _edit(upgrade=True)


def downgrade() -> None:
    _edit(upgrade=False)

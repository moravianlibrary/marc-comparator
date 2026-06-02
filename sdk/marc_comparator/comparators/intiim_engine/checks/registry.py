from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import identical, incomplete, nonstandard, typo

CHECKS: list[Callable[[str, str, str, dict[str, Any] | None], dict[str, Any] | None]] = [
    identical.run,
    typo.run,
    incomplete.run,
    nonstandard.run,
]

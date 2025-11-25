from __future__ import annotations
from typing import Callable, Optional, Dict, Any, List

from . import identical, incomplete, nonstandard, typo

CHECKS: List[Callable[[str, str, str, Optional[Dict[str, Any]]], Optional[Dict[str, Any]]]] = [
    identical.run,
    typo.run,
    incomplete.run,
    nonstandard.run,
]

from __future__ import annotations

from typing import Optional


TRACK_MISSING_TAGS = {
    "001",
    "015",
    "041",
    "245",
    "250",
    "260",
    "264",
    "300",
    "910",
}


TRACK_MISSING_SUBFIELDS = {
    ("020", "a"),
   
}


def is_missing_tracked(tag: str, code: Optional[str]) -> bool:
    if tag in TRACK_MISSING_TAGS:
        return True
    key = (tag, code)
    if key in TRACK_MISSING_SUBFIELDS:
        return True
    if (tag, None) in TRACK_MISSING_SUBFIELDS:
        return True
    return False

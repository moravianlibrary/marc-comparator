from __future__ import annotations

import re
from collections import Counter

_TOKEN_SPLIT_RE = re.compile(r"[^\w]+", re.UNICODE)
_ROMAN_NUMERAL_RE = re.compile(
    r"^(?=.)M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE,
)

PART_SENSITIVE_ROLES = {"title", "series_title", "edition"}


def _tokenize(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN_SPLIT_RE.split(text or "") if t]


def _is_part_token(token: str) -> bool:
    if not token:
        return False
    if token.isdigit():
        return len(token) <= 3
    return bool(_ROMAN_NUMERAL_RE.fullmatch(token))


def differs_only_by_part_tokens(a: str, b: str) -> bool:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb or ta == tb:
        return False
    fa = [t for t in ta if not _is_part_token(t)]
    fb = [t for t in tb if not _is_part_token(t)]
    if fa != fb:
        return False
    pa = Counter(t for t in ta if _is_part_token(t))
    pb = Counter(t for t in tb if _is_part_token(t))
    return pa != pb

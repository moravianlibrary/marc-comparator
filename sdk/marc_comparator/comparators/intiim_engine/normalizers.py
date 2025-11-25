from __future__ import annotations
import re, unicodedata
from typing import List, Set
from stdnum import isbn as std_isbn
from stdnum import issn as std_issn

LEADING_ARTICLES_EN = {"a", "an", "the"}
LEADING_ARTICLES_CS = {"ten", "ta", "to"}

ISO2_TO_3 = {
    "cs": "ces", "sk": "slk", "en": "eng", "de": "deu", "fr": "fra", "ru": "rus",
    "pl": "pol", "es": "spa", "it": "ita", "la": "lat"
}
THREE_TO_3 = {
    "cze": "ces", "ces": "ces",
    "slo": "slk", "slk": "slk",
    "ger": "deu", "deu": "deu",
    "fre": "fra", "fra": "fra",
}


def strip_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
def alnum_lower(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", s).lower()

def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s))

def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def _strip_edges(s: str) -> str:
    return s.strip(" .,:;/-()[]{}\"'")

def norm_generic(s: str) -> str:
    return _collapse_ws(_strip_edges(_nfkc(s))).casefold()

def _strip_isbd_trailing_colon(s: str) -> str:
    return re.sub(r"\s*:\s*$", "", str(s))

def _strip_isbd_trailing_comma(s: str) -> str:
    return re.sub(r"\s*,\s*$", "", str(s))

def _strip_brackets(s: str) -> str:
    s = str(s).strip()
    if s.startswith("[") and s.endswith("]"):
        return s[1:-1].strip()
    return s

def norm_place(s: str) -> str:
    return norm_generic(_strip_isbd_trailing_colon(s))

def norm_publisher(s: str) -> str:
    return norm_generic(_strip_isbd_trailing_comma(s))


_UDC_NUM_RE = re.compile(
    r"""
    (?P<num>
      \(?\d{1,3}(?:\.\d+)?      
      (?:                        
        (?:'\d+)+               
        |(?:\([^)]+\))          
      )*
    )
    """,
    re.X,
)

def norm_udc(s: str) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    m = _UDC_NUM_RE.search(t)
    return m.group("num") if m else t


def norm_title(s: str) -> str:
    s = norm_generic(s)
    parts = s.split()
    if parts and parts[0] in (LEADING_ARTICLES_EN | LEADING_ARTICLES_CS):
        s = " ".join(parts[1:])
    return s

def norm_name(s: str) -> str:
    s = norm_generic(s)
    if "," in s:
        last, _, rest = s.partition(",")
        s = f"{rest.strip()} {last.strip()}"
    return _collapse_ws(s)

def norm_year(s: str) -> str:
    s = _strip_brackets(s)
    m = re.search(r"(1[5-9]\d{2}|20\d{2}|21\d{2})", s)
    return m.group(0) if m else norm_generic(s)

def norm_isbn(s: str) -> str:
    s = str(s).replace("-", "").replace(" ", "")
    s = _nfkc(s)
    s = re.split(r"\s|\(", s)[0]
    try:
        s = std_isbn.compact(s)
        if std_isbn.is_valid(s):
            return std_isbn.format(s).replace("-", "")
    except Exception:
        pass
    return s.casefold()

def _split_langs(s: str) -> List[str]:
    return [t for t in re.split(r"[^A-Za-z]+", s) if t]

def norm_heading_text(s: str) -> str:
    return norm_generic(s)

def _canon_lang(code: str) -> str:
    c = code.lower()
    if len(c) == 2:
        return ISO2_TO_3.get(c, c)
    if len(c) == 3:
        return THREE_TO_3.get(c, c)
    return c

def norm_lang_mixed(s: str) -> str:
    toks = _split_langs(s)
    canons: Set[str] = set(_canon_lang(t) for t in toks)
    if not canons:
        return norm_generic(s)
    return "+".join(sorted(canons))

def norm_control_fixed(s: str) -> str:
    if s is None:
        return ""
    t = _nfkc(str(s)).ljust(40)
    year = t[7:11].strip().casefold()
    place = t[15:18].strip().casefold()
    lang = t[35:38].strip().casefold()
    return "|".join([year, place, lang])

def normalize_by_role(role: str, s: str) -> str:
    if role == "place":     return norm_place(s)
    if role == "publisher": return norm_publisher(s)
    if role == "isbn": return norm_isbn(s)
    if role == "title": return norm_title(s)
    if role == "name": return norm_name(s)
    if role == "year": return norm_year(s)
    if role == "udc":
        return norm_udc(s)
    if role == "lang_mixed": return norm_lang_mixed(s)
    if role == "control_fixed": return norm_control_fixed(s)
    if role in {"topical_heading","geographic_heading","genre_form","name_heading","chronological_heading","subject_code"}:
        return norm_heading_text(s)
    return norm_generic(s)

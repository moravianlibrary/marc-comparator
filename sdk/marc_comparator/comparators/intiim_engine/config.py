from __future__ import annotations

RECORD_CAP = 30
AGGREGATION = "lpnorm"
AGG_P = 2.0

HINGE_ACCEL_ENABLED = True
HINGE_POINT = 10.0
HINGE_EXP = 1.5

FIELD_ROLE = {
    # Control fields
    ("001", None): "control_id",
    ("003", None): "control_agency",
    ("005", None): "control_timestamp",
    ("007", None): "control_phys",
    ("008", None): "control_fixed",
    # 015 National bibliography number
    ("015", "a"): "nbn",
    # 020 ISBN and related
    ("020", "a"): "isbn",
    ("020", "q"): "material",
    ("020", "c"): "price",
    # 035 System control number
    ("035", "a"): "sysnum",
    # 040 Cataloging source & language of cataloging
    ("040", "a"): "org_code",
    ("040", "b"): "lang_mixed",
    ("040", "e"): "desc_standard",
    ("040", "d"): "org_code",
    # 041 Language codes (mixed 2/3)
    ("041", "a"): "lang_mixed",
    ("041", "h"): "lang_mixed",
    ("041", "b"): "lang_mixed",
    # 043 Geographic area codes (and source)
    ("043", "a"): "geo_code",
    ("043", "2"): "code_source",
    ("043", "b"): "geo_code",
    # 045 Time period
    ("045", "a"): "time_code",
    # 072 Subject category code
    ("072", "2"): "code_source",
    ("072", "9"): "local_code",
    ("072", "a"): "subject_code",
    ("072", "x"): "subject_subdivision",
    # 080 UDC
    ("080", "2"): "code_source",
    ("080", "a"): "udc",
    # 100 Main entry—Personal name
    ("100", "4"): "relator_code",
    ("100", "a"): "name",
    ("100", "7"): "authority_id",
    ("100", "d"): "date_life",
    # 240 Uniform title
    ("240", "a"): "title",
    ("240", "l"): "lang_mixed",
    # 245 Title statement
    ("245", "a"): "title",
    ("245", "b"): "title",
    ("245", "c"): "statement_of_responsibility",
    # 246 Variant title
    ("246", "a"): "title",
    # 250 Edition
    ("250", "a"): "edition",
    # 260/264 Publication
    ("260", "a"): "place",
    ("260", "b"): "publisher",
    ("260", "c"): "year",
    ("264", "a"): "place",
    ("264", "b"): "publisher",
    ("264", "c"): "year",
    # 300 Physical description
    ("300", "a"): "extent",
    ("300", "c"): "dimensions",
    ("300", "b"): "illustrations",
    # 336/337/338 RDA carrier/media/content
    ("336", "2"): "code_source",
    ("336", "a"): "rda_content",
    ("336", "b"): "rda_content_code",
    ("337", "2"): "code_source",
    ("337", "a"): "rda_media",
    ("337", "b"): "rda_media_code",
    ("338", "2"): "code_source",
    ("338", "a"): "rda_carrier",
    ("338", "b"): "rda_carrier_code",
    # 490 Series
    ("490", "a"): "series_title",
    # Notes
    ("500", "a"): "note",
    ("504", "a"): "note",
    ("521", "a"): "audience_note",
    ("546", "a"): "language_note",
    # 6XX Subjects (person/corp/time/topic/place)
    ("600", "a"): "name_heading",
    ("600", "7"): "authority_id",
    ("600", "2"): "code_source",
    ("600", "d"): "date_life",
    ("610", "a"): "name_heading",
    ("610", "7"): "authority_id",
    ("610", "2"): "code_source",
    ("648", "a"): "chronological_heading",
    ("648", "7"): "authority_id",
    ("648", "2"): "code_source",
    ("650", "2"): "code_source",
    ("650", "7"): "authority_id",
    ("650", "a"): "topical_heading",
    ("650", "z"): "geographic_subdivision",
    ("650", "y"): "chronological_subdivision",
    ("650", "x"): "topical_subdivision",
    ("651", "2"): "code_source",
    ("651", "a"): "geographic_heading",
    ("651", "7"): "authority_id",
    ("651", "x"): "topical_subdivision",
    ("655", "2"): "code_source",
    ("655", "a"): "genre_form",
    ("655", "7"): "authority_id",
    # 7XX Added entries
    ("700", "a"): "name",
    ("700", "4"): "relator_code",
    ("700", "7"): "authority_id",
    ("700", "d"): "date_life",
    ("710", "a"): "name",
    ("710", "7"): "authority_id",
    ("710", "4"): "relator_code",
    ("710", "b"): "subordinate_unit",
    # 8XX Series added entries
    ("830", "a"): "series_title",
    ("830", "0"): "authority_uri",
    # 9XX locals
    ("910", "b"): "local_code",
    ("910", "a"): "local_note",
    ("920", "a"): "local_note",
    ("920", "z"): "local_code",
    ("928", "a"): "local_note",
}

SIM_HIGH = 92
SIM_MED = 80
TOKEN_JACCARD_HIGH = 0.9
TOKEN_JACCARD_MED = 0.7

ASK_LLM_IF_UNSURE = True
CZECH_MODE = True

IGNORE_TAG_PATTERNS = ["9XX", "830", "040", "001", "003", "005"]

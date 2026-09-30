from marc_comparator.authority_linkers import AuthorityLinker, MarcXmlDumpLinkerConfig
from marc_comparator.authority_linkers.knihovny_cz_linker import (
    KnihovnyCZLinkerConfig,
)
from marc_comparator.comparators import EXCELLENT_MATCH, MATCH_SCALE_MAX
from pydantic import BaseModel, Field

from catalog_records.models import RecordFilter
from entities.settings import SettingsSchema

#: Confidence at which the first stage stops looking, on the comparator's 0-15
#: match scale. Matches the bottom of its "Excellent" band, which is what
#: scoring linkers report against.
DEFAULT_CONFIDENT_THRESHOLD = EXCELLENT_MATCH

#: How close behind a confident winner a runner-up has to be to be kept, in
#: points of the same 0-15 scale.
#:
#: A guess, and deliberately a setting rather than a constant. It can be tuned
#: once a pass has run with candidates stored, by looking at how often a kept
#: runner-up is ever consulted.
DEFAULT_CANDIDATE_MARGIN = 1.5


class AuthorityLinkingSettings(SettingsSchema):
    knihovny_cz: KnihovnyCZLinkerConfig | None = Field(
        default=KnihovnyCZLinkerConfig(), alias="knihovny-cz"
    )
    marcxml_dump: MarcXmlDumpLinkerConfig | None = Field(
        default=MarcXmlDumpLinkerConfig(), alias="marcxml-dump"
    )
    #: Confidence at which linking stops asking further linkers, on the
    #: comparator's 0-15 match scale. Below it every configured linker is
    #: consulted and the best proposal wins.
    confident_threshold: float = Field(
        default=DEFAULT_CONFIDENT_THRESHOLD, ge=0.0, le=MATCH_SCALE_MAX
    )
    #: How close behind a confident winner a runner-up has to score to be kept
    #: beside it, in points of the same 0-15 scale. A winner at 15.0 with a
    #: rival at 14.9 is ambiguous however good the score is — the catalogue
    #: holds two records matching ours — and those are the ones a cataloguer
    #: needs the alternatives for. Below `confident_threshold` the runner-ups
    #: are kept regardless.
    candidate_margin: float = Field(default=DEFAULT_CANDIDATE_MARGIN, ge=0.0, le=MATCH_SCALE_MAX)


class AuthorityLinkingTaskData(BaseModel):
    linkers: list[AuthorityLinker] = Field(..., min_length=1)
    target_base: str
    filters: RecordFilter = RecordFilter()

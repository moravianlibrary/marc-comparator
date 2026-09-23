from marc_comparator.authority_linkers import AuthorityLinker, MarcXmlDumpLinkerConfig
from marc_comparator.authority_linkers.knihovny_cz_linker import (
    KnihovnyCZLinkerConfig,
)
from pydantic import BaseModel, Field

from catalog_records.models import RecordFilter
from entities.settings import SettingsSchema


class AuthorityLinkingSettings(SettingsSchema):
    knihovny_cz: KnihovnyCZLinkerConfig | None = Field(
        default=KnihovnyCZLinkerConfig(), alias="knihovny-cz"
    )
    marcxml_dump: MarcXmlDumpLinkerConfig | None = Field(
        default=MarcXmlDumpLinkerConfig(), alias="marcxml-dump"
    )
    #: Confidence at which linking stops asking further linkers. Below it every
    #: configured linker is consulted and the best proposal wins.
    confident_threshold: float = Field(default=0.9, ge=0.0, le=1.0)


class AuthorityLinkingTaskData(BaseModel):
    linkers: list[AuthorityLinker] = Field(..., min_length=1)
    target_base: str
    filters: RecordFilter = RecordFilter()

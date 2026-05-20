from typing import List

from marc_comparator.authority_linkers import AuthorityLinker
from marc_comparator.authority_linkers.knihovny_cz_linker import (
    KnihovnyCZLinkerConfig,
)
from pydantic import BaseModel, Field

from catalog_records.models import RecordFilter
from entities.settings import SettingsSchema


class AuthorityLinkingSettings(SettingsSchema):
    knihovny_cz: KnihovnyCZLinkerConfig | None = Field(
        KnihovnyCZLinkerConfig(), alias="knihovny-cz"
    )


class AuthorityLinkingTaskData(BaseModel):
    linkers: List[AuthorityLinker] = Field(..., min_length=1)
    target_base: str
    filters: RecordFilter = RecordFilter()

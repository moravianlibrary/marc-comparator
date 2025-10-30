from typing import List

from marc_comparator_sdk.authority_linkers import AuthorityLinker
from marc_comparator_sdk.authority_linkers.knihovny_cz_linker import (
    KnihovnyCZLinkerConfig,
)
from pydantic import BaseModel

from adapters.indexer import IndexerQuery


class AuthorityLinkingSettings(BaseModel):
    enabled_linkers: List[AuthorityLinker]
    knihovny_cz: KnihovnyCZLinkerConfig | None = None


class AuthorityLinkingTaskData(BaseModel):
    target_base: str
    query: IndexerQuery

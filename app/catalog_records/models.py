from datetime import datetime
from typing import List

from aleph_nought import AlephOAIConfig
from marc_comparator.authority_linkers import AuthorityLinker
from marc_comparator.comparators import Comparator
from marc_comparator.validators import Validator
from pydantic import BaseModel, Field

from adapters.indexer import IndexerQuery
from entities.settings import SettingsSchema


class CatalogSettings(SettingsSchema):
    clients: List[AlephOAIConfig] = [
        AlephOAIConfig(
            base="MZK01",
            host="https://aleph.mzk.cz",
            endpoint="OAI",
            system_number_pattern=r"\d{9}",
            oai_sets=["MZK01-VDK"],
            oai_identifier_template="oai:aleph.mzk.cz:{base}-{doc_number}",
        )
    ]


class FetchRecordData(BaseModel):
    base: str
    system_number: str


class FetchBaseRecordsData(BaseModel):
    base: str
    system_numbers: List[str]


class FetchBatchOfRecordsData(BaseModel):
    per_base: List[FetchBaseRecordsData]


class SyncRecordsData(BaseModel):
    base: str
    from_date: datetime | None = None


class SetRecordsVisibilityData(BaseModel):
    query: IndexerQuery
    visible: bool = False


class ProcessRecordsSettings(SettingsSchema):
    target_bases: List[str] = Field(
        default=["MZK01"], min_length=1
    )
    authority_linkers: List[AuthorityLinker] = Field(
        default=[AuthorityLinker.KnihovnyCz], min_length=1
    )
    comparator: Comparator = Field(default=Comparator.Intiim)
    validators: List[Validator] = Field(
        default=[Validator.KrameriusLinks], min_length=1
    )

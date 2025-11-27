from datetime import datetime
from typing import List

from aleph_nought import AlephOAIConfig
from pydantic import BaseModel

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

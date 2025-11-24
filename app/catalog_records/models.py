from typing import List

from aleph_nought import AlephConfig
from marcdantic.context import MarcContext
from pydantic import BaseModel

from adapters.indexer import IndexerQuery
from entities.settings import SettingsSchema


class CatalogSettings(SettingsSchema):
    clients: List[AlephConfig]
    context: MarcContext = MarcContext()


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
    from_date: str | None = None


class SetRecordsHiddenStateData(BaseModel):
    query: IndexerQuery
    hide: bool = True

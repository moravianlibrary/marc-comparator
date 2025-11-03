from typing import List

from aleph_nought import AlephConfig
from pydantic import BaseModel

from entities.settings import SettingsSchema


class CatalogSettings(SettingsSchema):
    clients: List[AlephConfig]


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

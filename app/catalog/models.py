from pydantic import BaseModel


class FetchRecordData(BaseModel):
    base: str
    system_number: str


class SyncRecordsData(BaseModel):
    base: str
    from_date: str | None = None

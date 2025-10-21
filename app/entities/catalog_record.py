from datetime import datetime
from typing import Optional

from esorm.fields import Keyword
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    LargeBinary,
    String,
    event,
    func,
)

from adapters.database import Base, DatabaseSession
from adapters.indexer import IndexerSchema
from entities._operations import BaseOperationsMixin


class CatalogRecordSchema(IndexerSchema):
    class ESConfig:
        index = "catalog_records"
        id_field = "id"

    id: str

    base: Keyword
    system_number: Keyword

    last_sync: datetime
    deleted: bool


class CatalogRecord(Base, BaseOperationsMixin):
    __indexer_schema__ = CatalogRecordSchema
    __tablename__ = "catalog_records"

    id = Column(String, primary_key=True)
    base = Column(String, nullable=False)
    system_number = Column(String, nullable=False)

    marc = Column(LargeBinary, nullable=False)

    last_sync = Column(TIMESTAMP, nullable=False, default=func.now())
    deleted = Column(Boolean, nullable=False, default=False)

    @classmethod
    def generate_id(cls, base: str, system_number: str) -> str:
        return f"{base}-{system_number}"

    @classmethod
    def find_by_base_and_system_number(
        cls, db_session: DatabaseSession, base: str, system_number: str
    ) -> Optional["CatalogRecord"]:
        return cls.find(db_session, cls.generate_id(base, system_number))


@event.listens_for(CatalogRecord, "before_insert")
def set_id_before_insert(
    mapper,  # unused # noqa: F841
    connection,  # unused # noqa: F841
    target: CatalogRecord,
):
    if not target.id:
        target.id = CatalogRecord.generate_id(
            target.base, target.system_number
        )

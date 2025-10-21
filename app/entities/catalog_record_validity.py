from datetime import datetime
from enum import StrEnum

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

from adapters.database import Base
from adapters.indexer import IndexerSchema
from entities._operations import BaseOperationsMixin


class CatalogRecordValidity(Base, BaseOperationsMixin):
    pass

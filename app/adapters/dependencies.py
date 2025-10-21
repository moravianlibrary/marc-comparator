from typing import Annotated

from fastapi import Depends

from adapters.database import DatabaseSession, db_session_generator
from adapters.indexer import IndexerSession, get_indexer_session

DatabaseSessionDep = Annotated[DatabaseSession, Depends(db_session_generator)]
IndexerSessionDep = Annotated[IndexerSession, Depends(get_indexer_session)]

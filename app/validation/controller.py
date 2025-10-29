from typing import Annotated

from fastapi import APIRouter, Body

from auth.service import CurrentUser
from entities.task import TaskSchema
from adapters.dependencies import DatabaseSessionDep, IndexerSessionDep
from validation import service

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/", response_model=TaskSchema)
async def validate_records(
    query: Annotated[dict, Body(description="Elasticsearch DSL query")],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
) -> TaskSchema:

    # TODO: Add user check for permission Validate
    return await service.validate_record(query, current_user.user_id, db_session)

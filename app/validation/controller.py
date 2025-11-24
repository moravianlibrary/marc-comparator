from typing import Annotated

from fastapi import APIRouter, Body

from adapters.dependencies import DatabaseSessionDep, IndexerSessionDep
from auth.service import CurrentUser
from entities.task import TaskSchema

from . import service
from .models import ValidationTaskData

router = APIRouter(prefix="/validation", tags=["Validation"])


@router.post("/task", response_model=TaskSchema)
async def validate_records(
    data: Annotated[ValidationTaskData, Body(...)],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
    _: IndexerSessionDep,
):
    return await service.validate(data, current_user.user_id, db_session)

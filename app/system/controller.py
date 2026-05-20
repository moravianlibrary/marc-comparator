from typing import List

from fastapi import APIRouter

from adapters.dependencies import DatabaseSessionDep
from auth.service import CurrentUser
from system.models import SystemInfo

from . import service

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get("/info", response_model=SystemInfo)
async def get_system_info(
    db_session: DatabaseSessionDep,
    _: CurrentUser,
):
    return await service.get_system_info(db_session)


@router.get("/locks", response_model=List[str])
async def get_locks(_: CurrentUser):
    return service.get_locks()

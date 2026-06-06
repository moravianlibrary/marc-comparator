from fastapi import APIRouter
from fastapi.responses import JSONResponse

from adapters.dependencies import DatabaseSessionDep
from auth.service import CurrentUser
from system.models import SystemInfo

from . import service

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get("/health")
def health_check(db_session: DatabaseSessionDep):
    result = service.check_health(db_session)
    status_code = 200 if result.status == "ok" else 503
    return JSONResponse(content=result.model_dump(exclude_none=True), status_code=status_code)


@router.get("/info", response_model=SystemInfo)
async def get_system_info(
    db_session: DatabaseSessionDep,
    _: CurrentUser,
):
    return await service.get_system_info(db_session)


@router.get("/locks", response_model=list[str])
def get_locks(_: CurrentUser):
    return service.get_locks()

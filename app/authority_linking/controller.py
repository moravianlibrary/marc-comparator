from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status
from marcdantic import MarcRecord

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .models import AuthorityLinkingTaskData, LinkClaimRequest, LinkClaimSummary

router = APIRouter(
    prefix="/authority-linking",
    tags=["Authority Linking"],
    dependencies=[WithPermission(Permission.RunPartialRecordTasks)],
)


@router.post("/task", response_model=TaskSchema)
async def link_records_to_authorities(
    data: Annotated[AuthorityLinkingTaskData, Body(...)],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.authority_linking(data, current_user.user_id, db_session)


#: Claims live on their own router because they are a cataloguer's job, not an
#: operator's. The router above is gated on running linking tasks, and a
#: cataloguer who reviews records has no reason to hold that permission —
#: hanging these endpoints off it would have made the feature unreachable by
#: exactly the people it is for.
claims_router = APIRouter(
    prefix="/authority-linking",
    tags=["Authority Linking"],
    dependencies=[WithPermission(Permission.ReviewRecords)],
)


@claims_router.post(
    "/records/{main_record_id}/claims",
    response_model=LinkClaimSummary,
)
async def claim_link(
    main_record_id: str,
    request: Annotated[LinkClaimRequest, Body(...)],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    """Say whether a candidate is the match, and have the record say so too."""

    try:
        return await service.claim_link(main_record_id, request, current_user.user_id, db_session)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@claims_router.delete(
    "/records/{main_record_id}/claims/{base}/{authority_base}/{authority_sysno}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def withdraw_claim(
    main_record_id: str,
    base: str,
    authority_base: str,
    authority_sysno: str,
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    """Take a verdict back and let the linkers answer for themselves again."""

    await service.withdraw_claim(
        main_record_id, base, authority_base, authority_sysno, current_user.user_id, db_session
    )


@claims_router.get("/records/{main_record_id}/claims", response_model=list[LinkClaimSummary])
async def list_claims(
    main_record_id: str,
    db_session: DatabaseSessionDep,
    base: str | None = None,
):
    return service.claims_for_record(db_session, main_record_id, base)


#: And a third router, for the same reason there is a second one: a different
#: question needs a different permission. Reading a candidate is reading a
#: record we hold, no more privileged than reading our own — gating it on
#: `ReviewRecords` would hide the evidence from everyone who is not entitled
#: to rule on it, which is the wrong way round.
candidates_router = APIRouter(
    prefix="/authority-linking",
    tags=["Authority Linking"],
    dependencies=[WithPermission(Permission.ReadRecords)],
)


@candidates_router.get(
    "/candidates/{authority_base}/{authority_sysno}/marc",
    response_model=MarcRecord,
)
def get_candidate_marc(
    authority_base: str,
    authority_sysno: str,
    db_session: DatabaseSessionDep,
):
    """The MARC of a proposed record, so a verdict can be given on the record."""

    return service.get_candidate_marc(authority_base, authority_sysno, db_session)

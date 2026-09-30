from collections.abc import Sequence
from uuid import UUID

from marc_comparator.authority_linkers import AuthorityLinker

from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from catalog_records.models import RecordFilter
from config import config
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord
from entities.link_claim import ClaimVerdict, LinkClaim
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.service import get_settings_part

from .models import (
    AuthorityLinkingSettings,
    AuthorityLinkingTaskData,
    LinkClaimRequest,
    LinkClaimSummary,
)


async def authority_linking(
    data: AuthorityLinkingTaskData,
    created_by: str,
    db_session: DatabaseSession,
) -> TaskSchema:
    for linker in data.linkers:
        get_settings_part(SettingsScope.AuthorityLinking, linker.value, db_session)

    return await enqueue_task(
        Task(
            name=f"Authority linking for base '{data.target_base}'",
            type=TaskType.LinkRecordsToAuthorities,
            created_by=created_by,
            data=data.model_dump(),
        ),
        db_session,
    )


def _snapshot(
    rows: Sequence[AuthorityLink], authority_base: str, authority_sysno: str
) -> tuple[float | None, float | None]:
    """What the claimed candidate and its best rival scored, right now.

    Stored on the claim so that a later pass can ask the only question worth
    asking — has the evidence moved *against* this — rather than "has anything
    changed", which it always has.
    """

    claimed = next(
        (
            row.confidence
            for row in rows
            if (row.authority_base, row.authority_sysno) == (authority_base, authority_sysno)
        ),
        None,
    )
    rivals = [
        row.confidence
        for row in rows
        if (row.authority_base, row.authority_sysno) != (authority_base, authority_sysno)
        and row.confidence is not None
    ]
    return claimed, (max(rivals) if rivals else None)


async def claim_link(
    main_record_id: str,
    request: LinkClaimRequest,
    claimed_by: str,
    db_session: DatabaseSession,
) -> LinkClaimSummary:
    """Record a cataloguer's verdict, and ask for the record to be re-linked.

    The verdict is written here and now, so the interface can show it the
    moment it is given. Moving the rows is the other half, and it happens in
    the worker — see ``_reapply`` for why it cannot happen here.

    The snapshot is taken *before* the verdict is stored, because what makes a
    claim worth revisiting later is the gap it overruled, and after the claim
    is applied that gap is no longer visible anywhere.
    """

    record = db_session.get(CatalogRecord, main_record_id)
    if record is None:
        raise ValueError(f"No such record: {main_record_id}")

    rows = AuthorityLink.for_record_and_base(db_session, main_record_id, request.base)
    claimed_confidence, rival_confidence = _snapshot(
        rows, request.authority_base, request.authority_sysno
    )

    if request.verdict == ClaimVerdict.SameWork:
        # One answer per record and base: a cataloguer cannot hold that two
        # different records are both the match. A previous verdict on some
        # other candidate is withdrawn rather than left to compete.
        for existing in LinkClaim.for_record(db_session, main_record_id, request.base):
            if existing.is_same_work and existing.authority_key != (
                request.authority_base,
                request.authority_sysno,
            ):
                db_session.delete(existing)

    claim = db_session.get(
        LinkClaim,
        (main_record_id, request.base, request.authority_base, request.authority_sysno),
    )
    if claim is None:
        claim = LinkClaim(
            main_record_id=main_record_id,
            base=request.base,
            authority_base=request.authority_base,
            authority_sysno=request.authority_sysno,
        )
        db_session.add(claim)

    claim.verdict = request.verdict
    claim.note = request.note
    claim.claimed_by = UUID(claimed_by)
    claim.claimed_at = config.timestamp
    claim.claimed_confidence = claimed_confidence
    claim.rival_confidence = rival_confidence
    # A verdict just given is not one to second-guess.
    claim.needs_review = False
    db_session.commit()

    await _reapply(db_session, claimed_by, record.id, request.base)
    return LinkClaimSummary.model_validate(claim)


async def withdraw_claim(
    main_record_id: str,
    base: str,
    authority_base: str,
    authority_sysno: str,
    withdrawn_by: str,
    db_session: DatabaseSession,
) -> None:
    """Take a verdict back, and let the linkers answer for themselves again."""

    claim = db_session.get(LinkClaim, (main_record_id, base, authority_base, authority_sysno))
    if claim is None:
        return

    db_session.delete(claim)
    db_session.commit()

    await _reapply(db_session, withdrawn_by, main_record_id, base)


async def _reapply(
    db_session: DatabaseSession,
    created_by: str,
    main_record_id: str,
    base: str,
) -> TaskSchema | None:
    """Re-link one record so its stored rows catch up with the claims.

    The claim row itself is written synchronously, so the interface can show
    the verdict the moment it is given. The *rows* are another matter: writing
    them means running the linking pipeline, and this process does not have
    it — the API image ships no `tasks.py` on purpose, because the API does
    not run pipeline work.

    So it asks for the work instead of doing it, and asks for the ordinary
    kind: a linking pass scoped to this one record. That is better than a
    private path that only claims use — the record is re-linked by exactly the
    code that will handle the claim on every future pass, against live
    retrieval rather than against rows that may be stale, and a claim naming a
    record the last pass never returned is found again rather than rebuilt
    from storage.

    Returns None where no linker is configured; the claim still stands and
    the next full pass applies it.
    """

    settings = Settings.get(db_session, SettingsScope.AuthorityLinking, AuthorityLinkingSettings)
    if settings is None:
        return None

    configured = [
        linker
        for linker in AuthorityLinker
        if getattr(settings, linker.value.replace("-", "_"), None) is not None
    ]
    if not configured:
        return None

    return await enqueue_task(
        Task(
            name=f"Applying a cataloguer's verdict on {main_record_id}",
            type=TaskType.LinkRecordsToAuthorities,
            created_by=created_by,
            data=AuthorityLinkingTaskData(
                linkers=configured,
                target_base=base,
                filters=RecordFilter(record_ids=[main_record_id]),
            ).model_dump(),
        ),
        db_session,
    )


def claims_for_record(
    db_session: DatabaseSession, main_record_id: str, base: str | None = None
) -> list[LinkClaimSummary]:
    query = db_session.query(LinkClaim).filter_by(main_record_id=main_record_id)
    if base is not None:
        query = query.filter_by(base=base)
    return [
        LinkClaimSummary.model_validate(claim)
        for claim in query.order_by(LinkClaim.base, LinkClaim.claimed_at).all()
    ]

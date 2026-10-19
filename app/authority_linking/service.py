from collections.abc import Sequence
from uuid import UUID

from marc_comparator.comparators import RecordComparisonResult
from marcdantic import MarcRecord
from pydantic import ValidationError

from adapters.database import DatabaseSession
from adapters.marc_sectors import describe_marc_errors, read_marc, read_stored_marc
from adapters.tasks import enqueue_task
from catalog_records.models import ProcessRecordsSettings, RecordFilter
from catalog_records.service import get_marc_record
from comparison.tasks import load_gate_comparator
from config import config
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord
from entities.link_claim import ClaimVerdict, LinkClaim
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.service import get_settings_part

from .exceptions import (
    CandidateMarcNotStoredException,
    CandidateMarcUnreadableException,
    ComparatorUnavailableException,
)
from .models import (
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

    # The linkers a full pass would use, not every linker that has a config
    # object. Those two are not the same thing: every linker's config field
    # carries a default, so `is not None` was true of all of them and this
    # asked for linkers the operator had switched off — which on an install
    # without their harvest made the pass fail and take the record's rows
    # with it. The processing settings hold the actual choice.
    processing = Settings.get(db_session, SettingsScope.ProcessRecords, ProcessRecordsSettings)
    if processing is None:
        return None
    configured = list(processing.authority_linkers)
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


def get_candidate_marc(
    authority_base: str, authority_sysno: str, db_session: DatabaseSession
) -> MarcRecord:
    """The MARC of a record a linker proposed, accepted or not.

    The catalogue's own reader cannot serve these. It resolves a record row
    first, and a candidate deliberately has none — that is what keeps one
    cheap enough to store eight of per record. Sector storage has no such
    requirement: it is keyed by base and system number with no foreign key to
    the catalogue, which is exactly why ``store_candidate_marc`` writes there.
    So the bytes have been sitting in the same store as everything else, with
    nothing able to ask for them.

    Asking for them matters because of what a cataloguer is being asked to
    do. A claim says two records are or are not the same work, and until now
    the only thing in front of them was a system number and a score. Nobody
    can rule on that.

    Deliberately not restricted to the candidates of any one record: the
    answer does not depend on who is asking, and threading a record id
    through would only invite the caller to believe it did.
    """

    raw = read_marc(db_session, authority_base, authority_sysno)
    if raw is None:
        raise CandidateMarcNotStoredException(authority_base, authority_sysno)

    try:
        return read_stored_marc(raw)
    except ValidationError as e:
        # Before ValueError, which it subclasses — the same ordering trap the
        # catalogue's reader documents, and the same wrong answer if missed.
        raise CandidateMarcUnreadableException(
            authority_base, authority_sysno, describe_marc_errors(e)
        ) from e
    except ValueError as e:
        raise CandidateMarcUnreadableException(authority_base, authority_sysno, str(e)) from e


async def compare_candidate(
    main_base: str,
    main_sysno: str,
    authority_base: str,
    authority_sysno: str,
    db_session: DatabaseSession,
) -> RecordComparisonResult:
    """Compare one retained candidate on demand, without creating a comparison row."""

    main = get_marc_record(main_base, main_sysno, db_session)
    candidate = get_candidate_marc(authority_base, authority_sysno, db_session)

    # The gate comparator rather than the configured one, for two reasons
    # that happen to agree. It is the arithmetic that ranked these candidates
    # in the first place, so it is the score the reviewer is being asked
    # about; and it is the one that cannot reach an LLM. This endpoint is a
    # plain GET any reader may repeat at will, and the configured comparator
    # would let that call out to a model once per click.
    comparator, _is_pipeline_verdict = load_gate_comparator(db_session)
    if comparator is None:
        raise ComparatorUnavailableException

    return await comparator.run(main, candidate)

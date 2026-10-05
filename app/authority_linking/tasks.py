import logging
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from marc_comparator.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
    BaseAuthorityLinker,
    LinkProposal,
    LinkRequest,
)
from marc_comparator.authority_linkers import AuthorityLink as SdkAuthorityLink
from marcdantic import MarcRecord
from sqlalchemy import select

from adapters.database import DatabaseSession
from adapters.marc_sectors import (
    SectorBuffer,
    marc_bytes_of,
    read_marc_for_ids,
    read_marc_many,
    read_stored_marc,
    upsert_record_in_sector,
)
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from catalog_records.search import build_filtered_query
from config import config
from entities.authority_link import ANSWER_RANK, AuthorityLink, LinkOutcome
from entities.catalog_record import (
    CatalogRecord,
    CatalogRecordSource,
    cataloguing_agency_of,
)
from entities.link_claim import LinkClaim
from entities.settings import Settings, SettingsScope

from .claims import decide_with_claims
from .decision import Candidate, LinkDecision
from .models import (
    DEFAULT_CANDIDATE_MARGIN,
    DEFAULT_CONFIDENT_THRESHOLD,
    AuthorityLinkingSettings,
    AuthorityLinkingTaskData,
)

#: Everything here that can log takes a logger, because a task's logger writes
#: to that task's own log. The writers below sit under a caller that has none
#: to hand, and what they have to say is about the code rather than the run.
logger = logging.getLogger(__name__)


class LinkActionResult(StrEnum):
    NoLinkFound = "NoLinkFound"
    #: A lookup that never completed, which is not the same as no match. Kept
    #: apart in the summary because "found nothing" and "could not look" call
    #: for opposite responses: the first is an answer, the second is a retry.
    LinkingFailed = "LinkingFailed"
    DeletedLink = "DeletedLink"
    UpdatedLink = "UpdatedLink"
    ReplacedLink = "ReplacedLink"
    CreatedLink = "CreatedLink"
    CreatedAuthorityRecord = "CreatedAuthorityRecord"
    UnchangedLink = "UnchangedLink"
    UpdatedAuthorityRecord = "UpdatedAuthorityRecord"


@dataclass
class AuthorityLinkerInstance:
    linker: AuthorityLinker
    instance: BaseAuthorityLinker[Any]


class AuthorityLinkingFailed(RuntimeError):
    """No linker produced a result and at least one of them failed.

    Carries the base that was being tried, because the row recording the
    failure is written by the handler, and in the processing task that handler
    sits outside the loop which knows what was being looked up.
    """

    def __init__(self, message: str, target_base: str) -> None:
        super().__init__(message)
        self.target_base = target_base


def _confidence_of(link: SdkAuthorityLink) -> float:
    """A linker that reports no confidence is treated as the least certain.

    Confidences are not comparable across linkers in general: one may measure a
    match while another asserts a constant for every hit. Ranking them is only
    meaningful as a tie-break of last resort, which is all the second stage
    uses it for.
    """

    return link.confidence if link.confidence is not None else 0.0


def _matched_identifier_of(link: SdkAuthorityLink) -> str | None:
    """Which identifier retrieved it, where one did and the linker says so."""

    return link.matched_identifier


def _matched_by_of(link: SdkAuthorityLink) -> str | None:
    """The route as it is stored: a plain string, or nothing at all.

    A linker that retrieves one way has nothing to report here, and the column
    stays null rather than carrying a route invented on its behalf.
    """

    return link.matched_by.value if link.matched_by is not None else None


#: Records announced to the linkers in one go.
#:
#: A linker that asks a remote service per record is what a full pass spends
#: most of its time on, and announcing a window lets it collapse those into a
#: few requests. Sized against both ends: large enough that the per-record cost
#: is the batched one, small enough that the parsed MARC held for a window is a
#: few megabytes rather than the whole run.
LINK_PREFETCH_WINDOW = 200


def windows(items: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def announce_link_window(
    db_session: DatabaseSession,
    record_ids: Sequence[str],
    target_bases: Sequence[str],
    linkers: list[AuthorityLinkerInstance],
    logger: logging.Logger,
) -> dict[str, MarcRecord]:
    """Tell every linker what is about to be asked, and keep the MARC read.

    Reading a window costs one parse per record, which the caller pays anyway
    when it reaches that record, so the records are handed back rather than
    dropped and read a second time.
    """

    marc_by_id: dict[str, MarcRecord] = {}
    requests: list[LinkRequest] = []

    # A record missing from this is one with no MARC in storage. The caller
    # reports that when it reaches the record; a window is a hint, and must
    # not turn one record's problem into the batch's.
    for record_id, (base, system_number, raw) in read_marc_for_ids(db_session, record_ids).items():
        try:
            marc_record = read_stored_marc(raw)
        except ValueError:
            continue

        marc_by_id[record_id] = marc_record
        for target_base in target_bases:
            if target_base == base:
                continue
            requests.append(
                LinkRequest(
                    base=base,
                    system_number=system_number,
                    record=marc_record,
                    target_base=target_base,
                )
            )

    await announce_window(linkers, requests, logger, lambda linker: linker.linker.value)

    return marc_by_id


async def announce_window(
    plugins: Sequence[Any],
    announcement: Sequence[Any],
    logger: logging.Logger,
    name_of: Callable[[Any], str],
) -> None:
    """Warm each plugin's window, and let one that cannot warm its own pass.

    A prefetch is an optimisation: a plugin that fails here still answers
    record by record, which is slower rather than wrong, and not worth losing
    a batch over.
    """

    for plugin in plugins:
        try:
            await plugin.instance.prefetch(announcement)
        except Exception as e:
            logger.warning("Prefetch failed for %s: %s", name_of(plugin), e)


def load_authority_linkers(
    db_session: DatabaseSession,
    linkers: list[AuthorityLinker],
) -> list[AuthorityLinkerInstance] | None:
    """Load settings from DB and initialize linkers. Returns None on failure."""
    settings = Settings.get(db_session, SettingsScope.AuthorityLinking, AuthorityLinkingSettings)
    if not settings:
        return None
    result = init_authority_linkers(settings, linkers)
    from comparison.tasks import load_gate_comparator
    from harvest.storage import bind_plugin_storage

    # Ranking candidates on the configured scale rather than on whatever the
    # comparator class defaults to: otherwise a linker's minimum_confidence
    # means something other than the score an operator is shown.
    gate_comparator, _ = load_gate_comparator(db_session)
    for linker in result:
        bind_plugin_storage(
            linker.linker.value, linker.instance, db_session, logging.getLogger(__name__)
        )
        if gate_comparator is not None:
            linker.instance.bind_comparator(gate_comparator)
    return result or None


def load_confident_threshold(db_session: DatabaseSession) -> float:
    """The configured first-stage bar, or the default when nothing is stored."""

    settings = Settings.get(db_session, SettingsScope.AuthorityLinking, AuthorityLinkingSettings)
    return settings.confident_threshold if settings else DEFAULT_CONFIDENT_THRESHOLD


def load_candidate_margin(db_session: DatabaseSession) -> float:
    """The configured runner-up margin, or the default when nothing is stored."""

    settings = Settings.get(db_session, SettingsScope.AuthorityLinking, AuthorityLinkingSettings)
    return settings.candidate_margin if settings else DEFAULT_CANDIDATE_MARGIN


def init_authority_linkers(
    settings: AuthorityLinkingSettings,
    linkers: list[AuthorityLinker],
) -> list[AuthorityLinkerInstance]:
    """
    Initialize authority linkers from validated settings.
    Expects settings to be valid; skips linkers with missing class.
    """
    authority_linkers: list[AuthorityLinkerInstance] = []
    for linker in linkers:
        linker_cls = AUTHORITY_LINKER_DISPATCHER.get(linker)
        if not linker_cls:
            continue

        config_model = linker_cls.config_model
        if config_model is None:
            linker_instance = linker_cls()
        else:
            # Settings may store null for a configured linker; fall back to the
            # config model's own defaults rather than constructing without one.
            stored = getattr(settings, linker.value.replace("-", "_"), None)
            linker_instance = linker_cls(
                config_model.model_validate(stored) if stored is not None else config_model()
            )

        authority_linkers.append(AuthorityLinkerInstance(linker, linker_instance))

    return authority_linkers


def _merge_candidates(
    proposals: list[tuple[LinkProposal, AuthorityLinkerInstance]],
) -> list[Candidate]:
    """One ordered list out of several, deduplicated by the record named.

    Both linkers run for every record and can propose the same authority
    record, and the interface has to show a cataloguer one list. Ordering
    across linkers is not sound — ``_confidence_of`` says why — but it happens
    either way, and doing it here does it once, recorded, rather than
    implicitly on every read. Each row keeps its linker so a reader can see
    when an ordering crossed them.

    The higher confidence wins a duplicate. Between two linkers that is a
    coin toss dressed as a comparison; between the same record proposed twice
    it is the only answer available, and both name the same record either way.
    """

    best_by_record: dict[tuple[str, str], Candidate] = {}
    for proposal, linker in proposals:
        for link in proposal.candidates:
            key = (link.base, link.system_number)
            current = best_by_record.get(key)
            if current is None or _confidence_of(link) > _confidence_of(current.link):
                best_by_record[key] = Candidate(link, linker.linker.value)
    return sorted(best_by_record.values(), key=lambda c: _confidence_of(c.link), reverse=True)


async def find_best_link_for_record(
    catalog_record: CatalogRecord,
    authority_linkers: list[AuthorityLinkerInstance],
    target_base: str,
    marc_record: MarcRecord,
    logger: logging.Logger,
    confident_threshold: float = DEFAULT_CONFIDENT_THRESHOLD,
) -> LinkDecision:
    """
    Link a record in two stages.

    The first stage stops at the first linker confident enough to decide, in the
    order they are configured, so the rest are never asked. Only when no linker
    is confident does the second stage weigh every proposal and keep the best
    one — worth the extra work exactly because it is rare.

    A linker that reports a link is trusted about its own floor: its confidence
    is what it measured, and nothing here re-judges it beyond ranking.

    Raises ``AuthorityLinkingFailed`` when nothing was found and a linker
    failed. The caller treats "no link" as evidence that an existing link is
    obsolete and deletes it, so a lookup that never completed must not be
    reported as an empty result.
    """
    proposals: list[tuple[LinkProposal, AuthorityLinkerInstance]] = []
    failures: list[Exception] = []

    for authority_linker in authority_linkers:
        try:
            proposal = await authority_linker.instance.run(
                catalog_record.base,
                catalog_record.system_number,
                marc_record,
                target_base,
            )
        except Exception as e:
            failures.append(e)
            logger.error(
                f"Failed linking with {authority_linker.linker.value} "
                f"for record {catalog_record.id}: {e}"
            )
            continue

        proposals.append((proposal, authority_linker))
        if proposal.link is not None and _confidence_of(proposal.link) >= confident_threshold:
            # Confident and first in configured order: asking the remaining
            # linkers could only produce a rival to the same answer. Its own
            # runner-ups still come back — they are the alternatives to this
            # answer, and not asking the others is what makes them the only
            # ones there are.
            return LinkDecision(
                accepted=Candidate(proposal.link, authority_linker.linker.value),
                candidates=_merge_candidates([(proposal, authority_linker)]),
                candidate_count=proposal.candidate_count,
            )

    accepted = [
        (proposal.link, linker) for proposal, linker in proposals if proposal.link is not None
    ]

    if not accepted and failures:
        # Nothing was accepted and somebody never answered. The caller reads
        # "no link" as evidence that a standing link is obsolete and deletes
        # it, so anything short of "every linker answered and none matched"
        # must not reach it as an empty result — a shortlist that fell below
        # a floor while another linker was down included.
        raise AuthorityLinkingFailed(
            f"Every linker failed for record {catalog_record.id}", target_base
        ) from failures[0]

    candidates = _merge_candidates(proposals)
    candidate_count = sum(proposal.candidate_count for proposal, _ in proposals)

    if not accepted:
        return LinkDecision(accepted=None, candidates=candidates, candidate_count=candidate_count)

    best_link, best_linker = max(accepted, key=lambda item: _confidence_of(item[0]))
    logger.info(
        "No confident link for record %s; keeping the best of %d proposals (%s, confidence %.2f)",
        catalog_record.id,
        len(accepted),
        best_linker.linker.value,
        _confidence_of(best_link),
    )
    return LinkDecision(
        accepted=Candidate(best_link, best_linker.linker.value),
        candidates=candidates,
        candidate_count=candidate_count,
    )


def get_existing_link(
    db_session: DatabaseSession,
    main_record_id: str,
    base: str,
) -> AuthorityLink | None:
    """Return the single authority link for this record and base, if any."""
    return AuthorityLink.find_by_main_record_and_base(db_session, main_record_id, base)


def _answer_row(db_session: DatabaseSession, main_record_id: str, base: str) -> AuthorityLink:
    """The row holding this record's answer for this base, created if absent.

    Every outcome is written by rewriting this one row rather than deleting it
    and inserting another. That is not only cheaper: a delete and an insert of
    the same key in one flush are ordered by the unit of work, not by the code,
    and rewriting sidesteps the question entirely.
    """

    row = AuthorityLink.find_answer(db_session, main_record_id, base)
    if row is None:
        row = AuthorityLink(main_record_id=main_record_id, base=base, rank=ANSWER_RANK)
    return row


def _make_gap(
    row: AuthorityLink,
    outcome: LinkOutcome,
    detail: str | None,
    candidate_count: int | None = None,
) -> None:
    """Turn a row into a statement that there is no link, and why.

    Everything a link put there is cleared, including the linker: no single
    linker owns a gap. All of them were asked and none of them answered, so a
    name in that column would say one of them is responsible for a silence
    that was unanimous.
    """

    row.linker = None
    row.outcome = outcome
    row.authority_base = None
    row.authority_sysno = None
    row.authority_record_id = None
    row.confidence = None
    row.matched_by = None
    row.candidate_count = candidate_count
    row.detail = detail


def _apply_candidate(
    row: AuthorityLink,
    candidate: "Candidate",
    outcome: LinkOutcome,
    candidate_count: int | None = None,
    authority_record_id: str | None = None,
) -> None:
    """Write what a candidate is onto a row, whatever that row turned out to be.

    The same fields describe the accepted link, the best one that missed its
    floor and the runner-ups: what record it is, who proposed it, how it was
    found and what it scored. Only ``authority_record_id`` differs, and only
    because a candidate nobody accepted does not need a row in our catalogue:
    it has no comparison, no validation and no search text, and creating one
    would put it in every listing of records we hold.

    Its MARC is kept all the same — see ``store_candidate_marc``. The row is
    cheap because there is no catalogue entry, not because we let somebody
    else hold the record.
    """

    row.linker = candidate.linker
    row.outcome = outcome
    row.authority_base = candidate.link.base
    row.authority_sysno = candidate.link.system_number
    row.authority_record_id = authority_record_id
    row.confidence = candidate.link.confidence
    row.matched_by = _matched_by_of(candidate.link)
    row.matched_identifier = _matched_identifier_of(candidate.link)
    row.candidate_count = candidate_count
    row.detail = None


def _runner_ups(decision: "LinkDecision") -> list["Candidate"]:
    """Every candidate except the one sitting at the answer rank."""

    if decision.accepted is None:
        # Nothing was accepted, so the best candidate is what the answer rank
        # holds — as the reason there is no link.
        return decision.candidates[1:]
    key = (decision.accepted.link.base, decision.accepted.link.system_number)
    return [c for c in decision.candidates if (c.link.base, c.link.system_number) != key]


def candidates_worth_keeping(
    decision: "LinkDecision",
    confident_threshold: float,
    margin: float,
) -> list["Candidate"]:
    """The runner-ups worth putting in front of a cataloguer.

    Two separate reasons, because score alone is the wrong test.

    The first is doubt about the answer: below ``confident_threshold`` the
    system did not think this was obvious either, and that is the same number
    stage one stops looking at rather than a second one free to drift from it.

    The second is that a perfect score can still be ambiguous. A winner at
    1.00 with a runner-up at 0.99 means the union catalogue holds two records
    matching ours: either it has a duplicate or we are about to pick the wrong
    one of a pair. Those are precisely the cases somebody needs the
    alternatives for, and a score-only rule throws them away.
    """

    runners = _runner_ups(decision)
    if not runners:
        return []
    if decision.accepted is None:
        # The candidates are the entire evidence for the rejection. Pruning
        # them would leave a row saying "something was found and refused"
        # with nothing to show for it.
        return runners
    best = _confidence_of(decision.accepted.link)
    if best < confident_threshold:
        return runners
    return [c for c in runners if best - _confidence_of(c.link) <= margin]


def candidates_on_record(decision: "LinkDecision", wanted: list["Candidate"]) -> list["Candidate"]:
    """Every candidate this record ends up carrying a row for.

    Usually that is just the kept runner-ups. When nothing cleared its floor
    the best candidate is at the answer rank as well, holding the reason there
    is no link, and it is as much a stored candidate as the ones below it.

    The accepted link is not here: it has a catalogue record of its own, and
    the scenarios that write it store its MARC along with it.
    """

    if decision.accepted is None and decision.below_floor:
        return [decision.candidates[0], *wanted]
    return wanted


def _candidate_shape(row: AuthorityLink) -> tuple:
    return (
        row.authority_base,
        row.authority_sysno,
        row.confidence,
        row.linker,
        row.matched_identifier,
    )


def _wanted_shape(candidate: "Candidate") -> tuple:
    return (
        candidate.link.base,
        candidate.link.system_number,
        candidate.link.confidence,
        candidate.linker,
        _matched_identifier_of(candidate.link),
    )


def clear_stale_candidates(
    db_session: DatabaseSession,
    main_record_id: str,
    target_base: str,
    wanted: list["Candidate"],
) -> bool:
    """Drop the stored runner-ups unless they already say exactly ``wanted``.

    Returns whether the caller still has to write ``wanted`` — and the caller
    has to do that *after* the answer rank, not here, because the record being
    promoted to the answer is very often one of these rows. Writing the new
    list first would put it in the table twice: once as the runner-up it used
    to be, once as the answer it is about to become, which the primary key and
    the candidate index both refuse.

    So the three steps are ordered deletes, then the answer, then inserts, and
    each is flushed before the next. Rewriting wholesale rather than
    reconciling row by row for the same reason: two candidates trading places
    collide with each other in exactly the same way, and a rank is a position
    in an ordering, not an identity worth preserving.

    An unchanged list is left alone, which is what keeps a pass over
    already-linked records from rewriting rows that say the same thing — the
    same reason ``_link_update_would_write_nothing`` exists. That case is also
    safe by the argument above: for the answer to be taking over one of these
    rows, that row would have had to leave the wanted list, and then the list
    is not unchanged.
    """

    stored = (
        db_session.query(AuthorityLink)
        .filter(
            AuthorityLink.main_record_id == main_record_id,
            AuthorityLink.base == target_base,
            AuthorityLink.rank > ANSWER_RANK,
        )
        .order_by(AuthorityLink.rank)
        .all()
    )

    if [_candidate_shape(row) for row in stored] == [_wanted_shape(c) for c in wanted]:
        return False

    for row in stored:
        row.delete(db_session, commit=False)
    db_session.flush()
    return True


def write_candidates(
    db_session: DatabaseSession,
    main_record_id: str,
    target_base: str,
    wanted: list["Candidate"],
) -> None:
    """Fill the ranks below the answer, which ``clear_stale_candidates`` emptied."""

    for rank, candidate in enumerate(wanted, start=ANSWER_RANK + 1):
        row = AuthorityLink(main_record_id=main_record_id, base=target_base, rank=rank)
        _apply_candidate(row, candidate, LinkOutcome.Rejected)
        row.save(db_session, commit=False)


def record_below_floor(
    db_session: DatabaseSession,
    main_record_id: str,
    target_base: str,
    best: "Candidate",
    candidate_count: int,
) -> None:
    """Record that something was found and none of it was accepted.

    Unlike the other two gaps this one names a record, because there is one to
    name. It is deliberately not a link — no ``authority_record_id``, so no
    reader scoped to accepted links can reach it — while still telling a
    cataloguer which record was nearly chosen and what it scored. Without it,
    a rule set too strict is invisible: the records it refuses look exactly
    like the ones with no match in the catalogue at all.

    Which rule refused it matters, so the outcome distinguishes them. A score
    below the floor is a weak match and worth a look; a conflicting national
    bibliography number is a statement that these are different works, and no
    amount of looking will change it.
    """

    row = _answer_row(db_session, main_record_id, target_base)
    conflicts = _conflicts_of(best)
    _apply_candidate(
        row,
        best,
        LinkOutcome.Conflicting if conflicts else LinkOutcome.BelowFloor,
        candidate_count,
    )
    # _apply_candidate clears detail, so the reason goes on afterwards. It is
    # the only place the specific conflict survives: the outcome says a rule
    # refused this pair, and this says which.
    row.detail = ", ".join(conflicts) if conflicts else None
    row.save(db_session, commit=False)


def record_refused(
    db_session: DatabaseSession,
    main_record_id: str,
    target_base: str,
    best: "Candidate | None",
    candidate_count: int,
) -> None:
    """Record that a cataloguer ruled out what was found.

    Named separately from ``record_below_floor`` because the two call for
    opposite responses. A score below its floor is an invitation to look
    again, and raising or lowering the floor changes the answer. This is
    settled: a person read both records and said they are not a pair, and
    re-running the linkers will only produce the same refused candidate.

    It names a record where one survived the refusal and nothing where none
    did — a cataloguer who rules out the only candidate leaves a record with
    no counterpart, and there is nothing to point at.
    """

    row = _answer_row(db_session, main_record_id, target_base)
    if best is not None:
        _apply_candidate(row, best, LinkOutcome.Refused, candidate_count)
    else:
        row.linker = None
        row.outcome = LinkOutcome.Refused
        row.authority_base = None
        row.authority_sysno = None
        row.authority_record_id = None
        row.confidence = None
        row.matched_by = None
        row.candidate_count = candidate_count
    # _apply_candidate clears detail, so this goes on afterwards. Deliberately
    # not the claimant's name: who decided lives in `link_claims`, and a row
    # that answers "what is this record linked to" is not the place to put it.
    row.detail = "ruled out by a cataloguer"
    row.save(db_session, commit=False)


def _conflicts_of(candidate: "Candidate") -> list[str]:
    """What disqualified this candidate, as plain strings for the row.

    A linker that predates the veto reports nothing here, and a hand-rolled
    test double has no attribute at all — neither is a conflict, and neither
    should make the writer fail.
    """

    return [str(conflict) for conflict in getattr(candidate.link, "conflicts", None) or []]


def record_link_gap(
    db_session: DatabaseSession,
    main_record_id: str,
    target_base: str,
    outcome: LinkOutcome,
    detail: str | None = None,
    candidate_count: int | None = None,
) -> None:
    """Put the reason there is no link where the link would have been."""

    row = _answer_row(db_session, main_record_id, target_base)
    _make_gap(row, outcome, detail, candidate_count)
    row.save(db_session, commit=False)


def record_lookup_failure(
    db_session: DatabaseSession,
    main_record_id: str,
    target_base: str,
    detail: str,
) -> None:
    """Record that the lookup never completed — unless the record is linked.

    A lookup that failed says nothing about the record, which is why the
    caller does not delete an existing link over one. For exactly the same
    reason it must not overwrite one: where a link stands, the failure belongs
    in the log and the counters and nowhere else.
    """

    row = AuthorityLink.find_answer(db_session, main_record_id, target_base)
    if row is not None and row.outcome == LinkOutcome.Linked:
        return
    if row is None:
        row = AuthorityLink(main_record_id=main_record_id, base=target_base, rank=ANSWER_RANK)
    _make_gap(row, LinkOutcome.LookupFailed, detail)
    row.save(db_session, commit=False)


def scenario_no_link_no_existing(
    db_session: DatabaseSession,
    main_record_id: str,
    target_base: str,
    candidate_count: int = 0,
) -> list[LinkActionResult]:
    """No link found and none to remove; say so where the link would be."""
    record_link_gap(
        db_session,
        main_record_id,
        target_base,
        LinkOutcome.NoCandidate,
        candidate_count=candidate_count,
    )
    return [LinkActionResult.NoLinkFound]


def scenario_no_link_with_existing(
    db_session: DatabaseSession,
    existing_link: AuthorityLink,
    candidate_count: int = 0,
) -> list[LinkActionResult]:
    """No link found but one exists; retract it, and leave the reason behind.

    The link goes, which is the behaviour this has always had — a record the
    linkers no longer match is not linked. What is new is that the row stays,
    saying the lookup found nothing, so a link disappearing between passes is
    something a cataloguer can see rather than infer from its absence.
    """
    _make_gap(existing_link, LinkOutcome.NoCandidate, None, candidate_count)
    existing_link.save(db_session, commit=False)
    return [LinkActionResult.DeletedLink]


def store_authority_marc(
    db_session: DatabaseSession,
    base: str,
    system_number: str,
    marc: bytes,
    sectors: SectorBuffer | None,
) -> None:
    """Put an authority record's MARC where the rest of the system reads it.

    Written on its own, one record costs a whole sector: decompressed, merged,
    recompressed and re-indexed, with every record it shares the sector with
    dropped from the cache. That was measured at 189 ms a time and was the
    largest thing a processing pass did.

    Given a buffer the record waits there until its sector is written once for
    everything that landed in it. The caller owns the flushing, and owes the
    buffer a flush before anything reads the record back.
    """

    if sectors is None:
        upsert_record_in_sector(db_session, base, system_number, marc)
        return
    sectors.add(base, system_number, marc)


def store_candidate_marc(
    db_session: DatabaseSession,
    candidates: Sequence["Candidate"],
    sectors: SectorBuffer | None,
) -> None:
    """Keep our own copy of the MARC behind every candidate we record.

    A candidate still gets no ``catalog_records`` row — that is what keeps one
    cheap. What it must not be is a pointer into somebody else's table. The
    linker that found it holds the union catalogue in a plugin schema, and a
    plugin's tables are its own: to re-harvest, to rebuild, to drop when the
    plugin is disabled. A row saying "this record was nearly linked to SKC
    123456" is worth nothing the moment the only copy of SKC 123456 leaves
    with the harvest that fetched it.

    Sector storage is keyed by base and system number alone, with no foreign
    key to the catalogue, so a candidate's MARC lands beside the linked
    records' without a catalogue entry, a search vector or a comparison. At
    roughly half a kilobyte compressed that is the whole price of showing a
    cataloguer the alternative — and of promoting one later without asking a
    plugin for the record back.

    Written on every pass rather than only when the rows change: the store is
    keyed by what the record is, so re-storing an unchanged one is a no-op the
    sector buffer drops, and a candidate row written before this existed picks
    up its MARC the next time the record is linked.
    """

    for candidate in candidates:
        try:
            marc = marc_bytes_of(candidate.link.record)
        except ValueError:
            # A linker that assembles candidates rather than parsing them has
            # no bytes to keep. Worth saying out loud, because that candidate
            # cannot be promoted later — but not worth losing the row over.
            logger.warning(
                "Candidate %s:%s carries no raw MARC and was not stored",
                candidate.link.base,
                candidate.link.system_number,
            )
            continue
        store_authority_marc(
            db_session, candidate.link.base, candidate.link.system_number, marc, sectors
        )


def prefetch_linked_authority_marc(
    db_session: DatabaseSession,
    record_ids: Sequence[str],
    target_bases: Sequence[str],
) -> dict[str, bytes]:
    """Stored MARC of the authority records this window already links to.

    ``scenario_found_link_update`` can only decline to rewrite a record by
    comparing the linker's answer against what is stored, and read one record
    at a time that comparison costs more than the write it saves. Read for the
    whole window it is a couple of queries per sector.

    Keyed by authority record id, and plain bytes rather than ORM instances,
    so it survives the session cycling that happens mid-window.
    """

    rows = db_session.execute(
        select(
            AuthorityLink.authority_record_id,
            CatalogRecord.base,
            CatalogRecord.system_number,
        )
        .join(CatalogRecord, CatalogRecord.id == AuthorityLink.authority_record_id)
        .where(
            AuthorityLink.main_record_id.in_(record_ids),
            AuthorityLink.base.in_(target_bases),
            # Only the accepted links have an authority record behind them to
            # read; the join would drop the rest anyway, and saying so lets the
            # outcome index carry the work.
            AuthorityLink.rank == ANSWER_RANK,
            AuthorityLink.outcome == LinkOutcome.Linked,
        )
    ).all()

    by_base: defaultdict[str, list[str]] = defaultdict(list)
    ids_by_key: dict[tuple[str, str], str] = {}
    for authority_record_id, base, system_number in rows:
        by_base[base].append(system_number)
        ids_by_key[(base, system_number)] = authority_record_id

    stored: dict[str, bytes] = {}
    for base, system_numbers in by_base.items():
        for system_number, raw in read_marc_many(db_session, base, system_numbers).items():
            stored[ids_by_key[(base, system_number)]] = raw
    return stored


def _link_update_would_write_nothing(
    found_link: SdkAuthorityLink,
    linker_name: str | None,
    current_link: AuthorityLink,
    sectors: SectorBuffer | None,
    stored_marc: dict[str, bytes] | None,
    candidate_count: int | None = None,
) -> bool:
    """Whether re-running this link would store exactly what is already there.

    Everything the update writes is derived from these: the confidence on the
    link, the route the linker matched by, how many candidates it weighed, the
    linker that produced it, and the authority record's MARC. If none of them
    moved, the row, its search text and its sector all already say what this
    pass would say.

    Without a prefetched ``stored_marc`` this declines to decide rather than
    reading the record itself — one read per link to save one write per link
    is not a trade worth making, and the caller that prefetches is the one
    that walks every record.
    """

    if stored_marc is None:
        return False

    authority_record = current_link.linked_record
    if current_link.confidence != found_link.confidence:
        return False
    # A link written before the route was recorded has the same confidence it
    # always had, so without this the row would keep its null forever.
    if current_link.matched_by != _matched_by_of(found_link):
        return False
    # Same reasoning as the columns below: without this, every link written
    # before the column existed keeps a null identifier for good, because
    # nothing else about it will ever change.
    if current_link.matched_identifier != _matched_identifier_of(found_link):
        return False
    # Likewise for the natural key, which older rows were backfilled with and
    # which nothing but this writes. Checking it here is what makes a row that
    # somehow lost it heal on the next pass instead of keeping the gap.
    if (current_link.authority_base, current_link.authority_sysno) != (
        found_link.base,
        found_link.system_number,
    ):
        return False
    # Stored rather than derived: the unambiguous winners keep no runner-ups,
    # so this column is the only thing that can tell "one candidate" from
    # "eight, seven of them not worth keeping".
    if current_link.candidate_count != candidate_count:
        return False
    if authority_record.source_name != linker_name:
        return False
    # Same reasoning as `matched_by` above: a link written before this column
    # existed has the same confidence and the same MARC it always had, so
    # without this the authority record keeps its null agency forever and the
    # facet stays empty over 47,777 links that will never be rewritten.
    if authority_record.cataloguing_agency != cataloguing_agency_of(found_link.record):
        return False

    # A record waiting in the buffer still reads as its previous self, so the
    # stored bytes are about to be replaced by something this cannot see.
    if sectors is not None and sectors.holds(authority_record.base, authority_record.system_number):
        return False

    stored = stored_marc.get(authority_record.id)
    return stored is not None and stored == marc_bytes_of(found_link.record)


def scenario_found_link_update(
    db_session: DatabaseSession,
    found_link: SdkAuthorityLink,
    linker_name: str | None,
    current_link: AuthorityLink,
    sectors: SectorBuffer | None = None,
    stored_marc: dict[str, bytes] | None = None,
    candidate_count: int | None = None,
) -> list[LinkActionResult]:
    """Found link matches existing link; update in place.

    A pass over records that are already linked reaches here for every one of
    them, and used to rewrite the lot: the link row, the authority record's
    timestamp, its search text — three jq queries over the MARC — and its
    sector. Measured over 5296 records that was 2064 rewrites that changed
    nothing, and the search text alone was 9.7% of the task.
    """
    if _link_update_would_write_nothing(
        found_link, linker_name, current_link, sectors, stored_marc, candidate_count
    ):
        return [LinkActionResult.UnchangedLink]

    current_link.confidence = found_link.confidence
    current_link.matched_by = _matched_by_of(found_link)
    current_link.matched_identifier = _matched_identifier_of(found_link)
    current_link.authority_base = found_link.base
    current_link.authority_sysno = found_link.system_number
    current_link.candidate_count = candidate_count
    authority_record = current_link.linked_record
    authority_record.latest_sync = config.timestamp
    authority_record.source_name = linker_name
    authority_record.update_search_text_from(found_link.record)

    store_authority_marc(
        db_session,
        authority_record.base,
        authority_record.system_number,
        marc_bytes_of(found_link.record),
        sectors,
    )

    current_link.save(db_session, commit=False)
    return [
        LinkActionResult.UpdatedLink,
        LinkActionResult.UpdatedAuthorityRecord,
    ]


def _upsert_authority_record_and_link(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_name: str | None,
    target_base: str,
    sectors: SectorBuffer | None = None,
    candidate_count: int | None = None,
) -> tuple[CatalogRecord, LinkActionResult]:
    """Upsert the authority CatalogRecord, store its MARC, and create a new link."""
    authority_record = CatalogRecord.find_by_base_and_system_number(
        db_session, found_link.base, found_link.system_number
    )

    if not authority_record:
        authority_record = CatalogRecord(
            base=found_link.base,
            system_number=found_link.system_number,
            source_type=CatalogRecordSource.AuthorityLinker,
            source_name=linker_name,
        )
        record_result = LinkActionResult.CreatedAuthorityRecord
    else:
        authority_record.latest_sync = config.timestamp
        authority_record.source_name = linker_name
        record_result = LinkActionResult.UpdatedAuthorityRecord

    authority_record.update_search_text_from(found_link.record)
    authority_record.save(db_session, commit=False)
    store_authority_marc(
        db_session,
        found_link.base,
        found_link.system_number,
        marc_bytes_of(found_link.record),
        sectors,
    )

    # Into the answer slot, whatever is in it: a link this pass replaces, or a
    # row from the last pass saying there was nothing to link to.
    link = _answer_row(db_session, catalog_record.id, target_base)
    link.linker = linker_name
    link.outcome = LinkOutcome.Linked
    link.authority_base = found_link.base
    link.authority_sysno = found_link.system_number
    link.authority_record_id = authority_record.id
    link.confidence = found_link.confidence
    link.matched_by = _matched_by_of(found_link)
    link.matched_identifier = _matched_identifier_of(found_link)
    link.candidate_count = candidate_count
    link.detail = None
    link.save(db_session, commit=False)
    return authority_record, record_result


def scenario_found_link_replace(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_name: str | None,
    target_base: str,
    sectors: SectorBuffer | None = None,
    candidate_count: int | None = None,
) -> list[LinkActionResult]:
    """Found link points at a different authority record; take over the row.

    There is nothing to delete first. The link being replaced sits at the
    answer rank, which is exactly where the new one goes, so the write below
    overwrites it in place.
    """
    _, record_result = _upsert_authority_record_and_link(
        db_session,
        catalog_record,
        found_link,
        linker_name,
        target_base,
        sectors,
        candidate_count,
    )
    return [LinkActionResult.ReplacedLink, record_result]


def scenario_found_link_create(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    found_link: SdkAuthorityLink,
    linker_name: str | None,
    target_base: str,
    sectors: SectorBuffer | None = None,
    candidate_count: int | None = None,
) -> list[LinkActionResult]:
    """Found new link; create it (no existing link for this base)."""
    _, record_result = _upsert_authority_record_and_link(
        db_session,
        catalog_record,
        found_link,
        linker_name,
        target_base,
        sectors,
        candidate_count,
    )
    return [LinkActionResult.CreatedLink, record_result]


def handle_catalog_record_link_action(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    decision: LinkDecision,
    target_base: str,
    sectors: SectorBuffer | None = None,
    stored_marc: dict[str, bytes] | None = None,
    confident_threshold: float = DEFAULT_CONFIDENT_THRESHOLD,
    candidate_margin: float = DEFAULT_CANDIDATE_MARGIN,
) -> list[LinkActionResult]:
    """
    Write this record's whole list for this base: the answer, and the
    runner-ups worth keeping beside it. Returns LinkActionResult list.
    """
    existing_link = get_existing_link(db_session, catalog_record.id, target_base)

    # Emptied before the answer rank is touched and refilled after it, because
    # the record about to become the answer is often one of these rows.
    wanted = candidates_worth_keeping(decision, confident_threshold, candidate_margin)
    candidates_need_writing = clear_stale_candidates(
        db_session, catalog_record.id, target_base, wanted
    )

    results = _write_answer(
        db_session,
        catalog_record,
        decision,
        target_base,
        existing_link,
        sectors,
        stored_marc,
    )

    # Independent of whether the rows changed: the MARC store is keyed by the
    # record, not by the row, and this is what stops a candidate row from
    # being a pointer into a plugin's tables.
    store_candidate_marc(db_session, candidates_on_record(decision, wanted), sectors)

    if candidates_need_writing:
        write_candidates(db_session, catalog_record.id, target_base, wanted)
    return results


def _write_answer(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    decision: LinkDecision,
    target_base: str,
    existing_link: AuthorityLink | None,
    sectors: SectorBuffer | None,
    stored_marc: dict[str, bytes] | None,
) -> list[LinkActionResult]:
    """Put this record's answer for this base at the answer rank."""

    if decision.accepted is None:
        if decision.refused_by_cataloguer:
            # Checked before `below_floor`, because a refusal explains the
            # absent answer whether or not anything survived to be named.
            record_refused(
                db_session,
                catalog_record.id,
                target_base,
                decision.candidates[0] if decision.candidates else None,
                decision.candidate_count,
            )
            return [
                LinkActionResult.DeletedLink
                if existing_link is not None
                else LinkActionResult.NoLinkFound
            ]
        if decision.below_floor:
            # Something was found and refused. Distinct from finding nothing,
            # and the only way a floor set too high ever shows up.
            record_below_floor(
                db_session,
                catalog_record.id,
                target_base,
                decision.candidates[0],
                decision.candidate_count,
            )
            return [
                LinkActionResult.DeletedLink
                if existing_link is not None
                else LinkActionResult.NoLinkFound
            ]
        if existing_link is None:
            return scenario_no_link_no_existing(
                db_session, catalog_record.id, target_base, decision.candidate_count
            )
        return scenario_no_link_with_existing(db_session, existing_link, decision.candidate_count)

    found_link = decision.accepted.link
    linker_name = decision.accepted.linker

    if existing_link is None:
        return scenario_found_link_create(
            db_session,
            catalog_record,
            found_link,
            linker_name,
            target_base,
            sectors,
            decision.candidate_count,
        )

    if existing_link.system_number == found_link.system_number:
        return scenario_found_link_update(
            db_session,
            found_link,
            linker_name,
            existing_link,
            sectors,
            stored_marc,
            decision.candidate_count,
        )

    return scenario_found_link_replace(
        db_session,
        catalog_record,
        found_link,
        linker_name,
        target_base,
        sectors,
        decision.candidate_count,
    )


async def authority_linking(task_id: str) -> None:
    async with ManagedTask(task_id=task_id, lock_key=f"task-run-{task_id}") as ctx:
        data = AuthorityLinkingTaskData.model_validate(ctx.task.data)

        authority_linkers = load_authority_linkers(ctx.db_session, data.linkers)
        if not authority_linkers:
            ctx.logger.error("Authority linkers could not be initialized")
            return
        # The same comparator the linkers rank with, so a candidate rebuilt
        # from a claim scores on the scale everything else is on.
        from comparison.tasks import load_gate_comparator

        gate_comparator, _ = load_gate_comparator(ctx.db_session)
        confident_threshold = load_confident_threshold(ctx.db_session)
        candidate_margin = load_candidate_margin(ctx.db_session)

        counters: defaultdict[LinkActionResult, int] = defaultdict(int)

        # One record written on its own costs the whole sector it lives in,
        # and this task writes one per link it finds.
        sectors = SectorBuffer(lambda: ctx.db_session)
        ctx.before_commit = sectors.flush_all

        record_ids = [
            r.id
            for r in build_filtered_query(ctx.db_session, data.filters)
            .with_entities(CatalogRecord.id)
            .all()
        ]
        ctx.total = len(record_ids)

        for window in windows(record_ids, LINK_PREFETCH_WINDOW):
            window_marc = await announce_link_window(
                ctx.db_session, window, [data.target_base], authority_linkers, ctx.logger
            )

            CatalogRecord.warm(ctx.db_session, window)
            stored_marc = prefetch_linked_authority_marc(ctx.db_session, window, [data.target_base])
            # Most records carry no claim at all; one query per window is what
            # stops that from costing a query each to find out.
            claims_by_record = LinkClaim.for_records(ctx.db_session, window, data.target_base)

            for record_id in window:
                catalog_record = ctx.db_session.get(CatalogRecord, record_id)
                if catalog_record is None:
                    # Deleted between building the id list and getting here.
                    handle_batch_progress_snippet(ctx)
                    continue

                try:
                    if catalog_record.base == data.target_base:
                        handle_batch_progress_snippet(ctx)
                        continue

                    marc_record = window_marc.get(record_id) or catalog_record.get_record(
                        ctx.db_session
                    )

                    decision = await find_best_link_for_record(
                        catalog_record,
                        authority_linkers,
                        data.target_base,
                        marc_record,
                        ctx.logger,
                        confident_threshold,
                    )

                    # Last, and over the top of everything the linkers
                    # concluded: a claim is a person's verdict, not another
                    # signal to be weighed against the score.
                    claims = claims_by_record.get(record_id, [])
                    if claims:
                        decision, moved = await decide_with_claims(
                            ctx.db_session, decision, claims, marc_record, gate_comparator
                        )
                        for claim in moved:
                            claim.save(ctx.db_session, commit=False)

                    results = handle_catalog_record_link_action(
                        ctx.db_session,
                        catalog_record,
                        decision,
                        data.target_base,
                        sectors,
                        stored_marc,
                        confident_threshold,
                        candidate_margin,
                    )

                    for result in results:
                        counters[result] += 1

                    handle_batch_progress_snippet(ctx)

                except AuthorityLinkingFailed as e:
                    # find_best_link_for_record raises rather than returning
                    # None precisely so this is not read as "no match exists" —
                    # the caller deletes links it no longer finds. Counting it
                    # keeps that distinction in the summary instead of leaving
                    # it in the log, where a run that failed a thousand lookups
                    # reads like one that failed none.
                    counters[LinkActionResult.LinkingFailed] += 1
                    record_lookup_failure(ctx.db_session, catalog_record.id, e.target_base, str(e))
                    ctx.logger.error(f"Linking failed for record {catalog_record.id}: {e}")
                    handle_batch_progress_snippet(ctx)

                except ValueError as e:
                    ctx.logger.warning(f"Skipping record {catalog_record.id}: {e}")
                    handle_batch_progress_snippet(ctx)

                except Exception as e:
                    ctx.db_session.rollback()
                    ctx.logger.error(f"Failed linking record {catalog_record.id}:\n{e}")
                    handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(f"Finished authority linking, total records processed: {ctx.progress}")
        ctx.logger.info(
            "Summary of link actions: %s",
            {result.value: count for result, count in counters.items()},
        )

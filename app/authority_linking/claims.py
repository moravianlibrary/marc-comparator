"""What a cataloguer said, applied over what the linkers concluded.

Everything else in this package is a machine's opinion: a linker retrieves
candidates, a comparator scores them, a floor accepts or refuses one. This
module is the one place where a person's verdict enters, and it is deliberately
the last word — a claim is not another signal to be weighed against the score,
it replaces the answer.

Two rules follow from that, and both were asked for:

**A claim does not lapse because the numbers moved.** Scores change on every
pass, most often because somebody fixed one of the two catalogues, which is
what this tool exists to cause. A claimed link whose score improves has not
become more doubtful, and one whose rival improves has not been overruled. So
the claim keeps deciding, and the only thing that changes is whether it is
flagged for a second look — see ``LinkClaim.margin_moved_against``, which
compares the *gap* the cataloguer already overruled against the gap now.

**A claim can name a record this pass did not find.** Retrieval is generous
but not exhaustive, and the case a claim exists for is exactly the one the
machine got wrong. The claimed record's MARC is ours — every candidate's has
been since the pipeline stopped pointing into plugin tables — so a candidate
can be rebuilt from storage and scored like any other.
"""

import logging
from collections.abc import Sequence

from marc_comparator.authority_linkers import AuthorityLink as SdkAuthorityLink
from marc_comparator.comparators import BaseComparator
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.marc_sectors import read_marc_many, read_stored_marc
from entities.link_claim import ClaimVerdict, LinkClaim

from .decision import Candidate, LinkDecision

logger = logging.getLogger(__name__)


def _key(candidate: Candidate) -> tuple[str, str]:
    return (candidate.link.base, candidate.link.system_number)


def _best_rival(candidates: Sequence[Candidate], except_key: tuple[str, str]) -> float | None:
    """The best confidence among candidates other than one.

    None where there is no rival at all, which is not the same as a rival
    scoring zero: the first says nothing was competing, the second says
    something was and lost badly.
    """

    rivals = [
        candidate.link.confidence
        for candidate in candidates
        if _key(candidate) != except_key and candidate.link.confidence is not None
    ]
    return max(rivals) if rivals else None


def same_work_claim(claims: Sequence[LinkClaim]) -> LinkClaim | None:
    """The claim that names the answer, or nothing where none does.

    At most one should exist per record and base — a cataloguer cannot hold
    that two different records are both the match, and the service enforces
    it by clearing the previous one. Taking the newest defends the read side
    against a row that got in some other way.
    """

    accepted = [claim for claim in claims if claim.is_same_work]
    if not accepted:
        return None
    return max(accepted, key=lambda claim: claim.claimed_at)


def rejected_keys(claims: Sequence[LinkClaim]) -> set[tuple[str, str]]:
    return {claim.authority_key for claim in claims if not claim.is_same_work}


async def candidate_from_storage(
    db_session: DatabaseSession,
    claim: LinkClaim,
    ours: MarcRecord,
    comparator: BaseComparator | None,
) -> Candidate | None:
    """Rebuild a claimed candidate that retrieval did not return this pass.

    Read out of our own sector storage by the natural key the claim carries,
    and scored with the pipeline's comparator so its confidence means the same
    thing as every other candidate's. Where there is no comparator the
    candidate still stands — the claim decides the answer, not the score — it
    simply has no number beside it.

    ``linker`` is left empty on purpose: no linker proposed this record, and
    saying one did would credit it with a find it did not make.
    """

    raw = read_marc_many(db_session, claim.authority_base, [claim.authority_sysno]).get(
        claim.authority_sysno
    )
    if raw is None:
        logger.warning(
            "Claimed record %s:%s has no stored MARC; the claim cannot be applied this pass",
            claim.authority_base,
            claim.authority_sysno,
        )
        return None

    try:
        theirs = read_stored_marc(raw)
    except Exception as e:
        logger.warning(
            "Claimed record %s:%s could not be read: %s",
            claim.authority_base,
            claim.authority_sysno,
            e,
        )
        return None

    comparison = None
    confidence = None
    if comparator is not None:
        try:
            comparison = await comparator.run(ours, theirs)
            confidence = comparison.overall_score
        except Exception as e:
            logger.warning(
                "Claimed record %s:%s could not be scored: %s",
                claim.authority_base,
                claim.authority_sysno,
                e,
            )

    return Candidate(
        link=SdkAuthorityLink(
            base=claim.authority_base,
            system_number=claim.authority_sysno,
            record=theirs,
            confidence=confidence,
            comparison=comparison,
        ),
        linker=None,
    )


def apply_claims(decision: LinkDecision, claims: Sequence[LinkClaim]) -> LinkDecision:
    """The decision as it stands once the cataloguers have had their say.

    A ``NotSameWork`` claim removes the candidate outright, which is what the
    verdict means: the two records are not a pair, so it is not a candidate and
    it is not an alternative worth showing again. A ``SameWork`` claim takes
    the answer, whatever it scored and whatever the machine preferred.

    Where the claimed record is not among the candidates the decision is
    returned unchanged — the caller is expected to have offered it from
    storage first, and if that failed there is nothing here to promote.
    """

    if not claims:
        return decision

    refused = rejected_keys(claims)
    surviving = [c for c in decision.candidates if _key(c) not in refused]

    claimed = same_work_claim(claims)
    if claimed is not None:
        wanted = next((c for c in surviving if _key(c) == claimed.authority_key), None)
        if wanted is not None:
            return LinkDecision(
                accepted=wanted,
                # The claimed record first, then the rest in their own order,
                # so the stored ranks read the way the record is now answered.
                candidates=[wanted, *(c for c in surviving if _key(c) != claimed.authority_key)],
                candidate_count=decision.candidate_count,
                refused_by_cataloguer=bool(refused),
            )

    accepted = decision.accepted
    if accepted is not None and _key(accepted) in refused:
        # The machine's answer was ruled out and nothing was claimed in its
        # place. Promoting the next candidate is not available: only the
        # accepted one is known to have cleared a floor, and the rest are a
        # shortlist, not a queue of approved answers.
        accepted = None

    return LinkDecision(
        accepted=accepted,
        candidates=surviving,
        candidate_count=decision.candidate_count,
        refused_by_cataloguer=bool(refused),
    )


def refresh_review_flags(decision: LinkDecision, claims: Sequence[LinkClaim]) -> list[LinkClaim]:
    """Re-evaluate every claim against this pass, returning the ones that moved.

    Only the flag moves. A claim is never withdrawn here, because nothing in
    this module is entitled to withdraw one: the numbers changing is not an
    argument against a person who looked at both records.
    """

    by_key = {_key(candidate): candidate for candidate in decision.candidates}
    changed: list[LinkClaim] = []

    for claim in claims:
        if claim.verdict != ClaimVerdict.SameWork:
            continue

        candidate = by_key.get(claim.authority_key)
        claimed_now = candidate.link.confidence if candidate is not None else None
        rival_now = _best_rival(decision.candidates, claim.authority_key)

        # A claimed record retrieval no longer returns is worth a look on its
        # own account: it may have left the target catalogue.
        wanted = candidate is None or claim.margin_moved_against(claimed_now, rival_now)

        if wanted != claim.needs_review:
            claim.needs_review = wanted
            changed.append(claim)

    return changed


async def decide_with_claims(
    db_session: DatabaseSession,
    decision: LinkDecision,
    claims: Sequence[LinkClaim],
    ours: MarcRecord,
    comparator: BaseComparator | None,
) -> tuple[LinkDecision, list[LinkClaim]]:
    """The whole of a cataloguer's say, in the order it has to happen.

    A claimed record retrieval missed is offered from storage first, so that
    ``apply_claims`` has something to promote; then the claims are applied;
    then every claim is re-checked against the decision that came out. The
    review flags are computed last on purpose — they describe the answer as it
    now stands, not the one the linkers would have given.
    """

    if not claims:
        return decision, []

    claimed = same_work_claim(claims)
    if claimed is not None and not any(
        _key(candidate) == claimed.authority_key for candidate in decision.candidates
    ):
        rebuilt = await candidate_from_storage(db_session, claimed, ours, comparator)
        if rebuilt is not None:
            decision = LinkDecision(
                accepted=decision.accepted,
                candidates=[*decision.candidates, rebuilt],
                candidate_count=decision.candidate_count,
            )

    decided = apply_claims(decision, claims)
    return decided, refresh_review_flags(decided, claims)

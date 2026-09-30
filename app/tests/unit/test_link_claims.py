"""A cataloguer's verdict is the last word, and does not lapse when scores move.

The linkers produce an opinion every pass. A claim is the one statement in the
system that is not one, so the tests here are mostly about what must *not*
happen to it: it is not outvoted by a better-scoring rival, it is not withdrawn
because the numbers moved, and it does not quietly become a suggestion.
"""

from datetime import datetime, timedelta

import pytest
from marc_comparator.authority_linkers import AuthorityLink as SdkAuthorityLink
from marcdantic import MarcRecord

# Constructing any mapped class configures every mapper, and the relationships
# on these are declared by name, so all of them have to be imported first.
import entities.catalog_record  # noqa: F401
import entities.role  # noqa: F401
import entities.user  # noqa: F401
from authority_linking.claims import (
    apply_claims,
    refresh_review_flags,
    same_work_claim,
)
from authority_linking.decision import Candidate, LinkDecision
from entities.link_claim import ClaimVerdict, LinkClaim

BASE = "SKC"
WHEN = datetime(2026, 9, 1, 12, 0, 0)


def _candidate(sysno: str, confidence: float | None, linker: str | None = "marcxml-dump"):
    return Candidate(
        link=SdkAuthorityLink(
            base=BASE,
            system_number=sysno,
            record=MarcRecord.model_construct(),
            confidence=confidence,
        ),
        linker=linker,
    )


def _decision(*candidates: Candidate, accepted: int | None = 0) -> LinkDecision:
    return LinkDecision(
        accepted=candidates[accepted] if accepted is not None and candidates else None,
        candidates=list(candidates),
        candidate_count=len(candidates),
    )


def _claim(
    sysno: str,
    verdict: ClaimVerdict = ClaimVerdict.SameWork,
    *,
    claimed: float | None = None,
    rival: float | None = None,
    at: datetime = WHEN,
    needs_review: bool = False,
) -> LinkClaim:
    return LinkClaim(
        main_record_id="MZK01-000000001",
        base=BASE,
        authority_base=BASE,
        authority_sysno=sysno,
        verdict=verdict,
        claimed_at=at,
        claimed_confidence=claimed,
        rival_confidence=rival,
        needs_review=needs_review,
    )


class TestTheClaimDecidesTheAnswer:
    def test_a_claimed_candidate_takes_the_answer_from_a_better_score(self):
        decision = _decision(_candidate("111", 14.0), _candidate("222", 8.0))

        decided = apply_claims(decision, [_claim("222")])

        assert decided.accepted is not None
        assert decided.accepted.link.system_number == "222"

    def test_the_claimed_candidate_leads_the_list(self):
        decision = _decision(_candidate("111", 14.0), _candidate("222", 8.0))

        decided = apply_claims(decision, [_claim("222")])

        assert [c.link.system_number for c in decided.candidates] == ["222", "111"]

    def test_a_claim_on_what_was_already_chosen_changes_nothing_visible(self):
        decision = _decision(_candidate("111", 14.0), _candidate("222", 8.0))

        decided = apply_claims(decision, [_claim("111")])

        assert decided.accepted is not None
        assert decided.accepted.link.system_number == "111"

    def test_no_claims_is_the_decision_untouched(self):
        decision = _decision(_candidate("111", 14.0))

        assert apply_claims(decision, []) is decision


class TestARefusalIsNotAPromotion:
    def test_a_refused_candidate_leaves_the_list(self):
        decision = _decision(_candidate("111", 14.0), _candidate("222", 8.0))

        decided = apply_claims(decision, [_claim("222", ClaimVerdict.NotSameWork)])

        assert [c.link.system_number for c in decided.candidates] == ["111"]

    def test_refusing_the_answer_leaves_no_answer_rather_than_the_runner_up(self):
        # Only the accepted candidate is known to have cleared a floor. The
        # rest are a shortlist, not a queue of approved answers, and promoting
        # one would accept something a linker refused.
        decision = _decision(_candidate("111", 14.0), _candidate("222", 8.0))

        decided = apply_claims(decision, [_claim("111", ClaimVerdict.NotSameWork)])

        assert decided.accepted is None
        assert [c.link.system_number for c in decided.candidates] == ["222"]

    def test_a_refusal_says_why_there_is_no_answer(self):
        decision = _decision(_candidate("111", 14.0))

        decided = apply_claims(decision, [_claim("111", ClaimVerdict.NotSameWork)])

        assert decided.refused_by_cataloguer
        assert decided.accepted is None

    def test_a_refusal_elsewhere_does_not_disturb_the_answer(self):
        decision = _decision(_candidate("111", 14.0), _candidate("222", 8.0))

        decided = apply_claims(decision, [_claim("222", ClaimVerdict.NotSameWork)])

        assert decided.accepted is not None
        assert decided.accepted.link.system_number == "111"

    def test_a_claim_outranks_a_refusal_of_everything_else(self):
        decision = _decision(_candidate("111", 14.0), _candidate("222", 8.0))

        decided = apply_claims(
            decision,
            [_claim("111", ClaimVerdict.NotSameWork), _claim("222")],
        )

        assert decided.accepted is not None
        assert decided.accepted.link.system_number == "222"


class TestOneAnswerPerRecord:
    def test_the_newest_verdict_is_the_one_that_stands(self):
        older = _claim("111", at=WHEN)
        newer = _claim("222", at=WHEN + timedelta(days=1))

        assert same_work_claim([older, newer]) is newer

    def test_refusals_are_not_answers(self):
        assert same_work_claim([_claim("111", ClaimVerdict.NotSameWork)]) is None


class TestTheGapDecidesWhetherToAskAgain:
    @pytest.mark.parametrize(
        ("claimed_then", "rival_then", "claimed_now", "rival_now", "expected"),
        [
            # The cataloguer already overruled a rival two points ahead.
            (10.0, 12.0, 10.0, 12.0, False),
            # It pulled a further point ahead: worth another look.
            (10.0, 12.0, 10.0, 13.0, True),
            # It fell back: nothing to ask about.
            (10.0, 12.0, 10.0, 11.0, False),
            # The claimed record improved, which is what fixing a catalogue
            # looks like, and is not evidence against the claim.
            (10.0, 12.0, 14.0, 12.0, False),
            # Both improved by the same amount: the gap is unchanged.
            (10.0, 12.0, 12.0, 14.0, False),
        ],
    )
    def test_only_the_gap_moving_against_it_counts(
        self, claimed_then, rival_then, claimed_now, rival_now, expected
    ):
        claim = _claim("222", claimed=claimed_then, rival=rival_then)

        assert claim.margin_moved_against(claimed_now, rival_now) is expected

    def test_a_claim_with_no_snapshot_never_asks_on_this_ground(self):
        claim = _claim("222", claimed=None, rival=None)

        assert claim.margin_moved_against(10.0, 15.0) is False

    def test_a_claim_made_against_no_rival_at_all_asks_nothing(self):
        claim = _claim("222", claimed=10.0, rival=None)

        assert claim.margin_moved_against(10.0, 15.0) is False


class TestFlaggingNeverWithdraws:
    def test_a_rival_pulling_ahead_raises_the_flag_and_nothing_else(self):
        claim = _claim("222", claimed=10.0, rival=12.0)
        decision = _decision(_candidate("111", 13.5), _candidate("222", 10.0), accepted=1)

        moved = refresh_review_flags(decision, [claim])

        assert moved == [claim]
        assert claim.needs_review
        assert claim.verdict == ClaimVerdict.SameWork

    def test_a_flag_is_lowered_when_the_gap_comes_back(self):
        claim = _claim("222", claimed=10.0, rival=12.0, needs_review=True)
        decision = _decision(_candidate("222", 14.0), _candidate("111", 12.0))

        moved = refresh_review_flags(decision, [claim])

        assert moved == [claim]
        assert not claim.needs_review

    def test_an_unchanged_flag_is_not_reported_as_moved(self):
        claim = _claim("222", claimed=10.0, rival=12.0)
        decision = _decision(_candidate("222", 10.0), _candidate("111", 12.0))

        assert refresh_review_flags(decision, [claim]) == []

    def test_a_claimed_record_that_stopped_being_found_is_worth_a_look(self):
        # It may have left the target catalogue, which nothing else reports.
        claim = _claim("222", claimed=10.0, rival=12.0)
        decision = _decision(_candidate("111", 12.0))

        refresh_review_flags(decision, [claim])

        assert claim.needs_review

    def test_a_refusal_is_never_flagged(self):
        claim = _claim("222", ClaimVerdict.NotSameWork, claimed=10.0, rival=12.0)
        decision = _decision(_candidate("111", 15.0))

        assert refresh_review_flags(decision, [claim]) == []
        assert not claim.needs_review

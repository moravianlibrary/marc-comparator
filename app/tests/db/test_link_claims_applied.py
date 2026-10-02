"""A claim has to change the record, not merely be recorded against it.

Two halves, because the work is split across two processes. The API writes the
claim and asks for the record to be re-linked — it cannot do the re-linking
itself, since the API image ships no pipeline code on purpose. The worker then
runs the pass, and that is where the claim actually moves rows.

What is exercised here is the worker's half against real rows, and the API's
half up to the point where it hands over.
"""

from uuid import uuid4

import pytest
from marc_comparator.authority_linkers import AuthorityLink as SdkAuthorityLink
from marc_comparator.authority_linkers import MatchRoute

from adapters.marc_sectors import marc_bytes_of
from authority_linking import service
from authority_linking.claims import decide_with_claims
from authority_linking.decision import Candidate, LinkDecision
from authority_linking.models import LinkClaimRequest
from authority_linking.tasks import handle_catalog_record_link_action, store_authority_marc
from entities.authority_link import ANSWER_RANK, AuthorityLink, LinkOutcome
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.link_claim import ClaimVerdict, LinkClaim
from entities.user import User
from tests.conftest import load_test_record

pytestmark = pytest.mark.db

TARGET_BASE = "SKC"


def _record(db_session, system_number: str) -> CatalogRecord:
    record = CatalogRecord(
        base="MZK01",
        system_number=system_number,
        source_type=CatalogRecordSource.Main,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    store_authority_marc(
        db_session,
        record.base,
        record.system_number,
        marc_bytes_of(load_test_record("MZK01-001217709.mrc")),
        None,
    )
    db_session.commit()
    return record


def _candidate(system_number: str, confidence: float, linker: str = "marcxml-dump") -> Candidate:
    link = SdkAuthorityLink(
        base=TARGET_BASE,
        system_number=system_number,
        record=load_test_record("MZK01-001217709.mrc"),
        confidence=confidence,
        matched_by=MatchRoute.Identifier,
        matched_identifier="isbn",
    )
    return Candidate(link, linker)


def _cataloguer(db_session) -> User:
    """Somebody for the claim to belong to. Its foreign key needs a real row."""

    user = User(
        id=uuid4(),
        email=f"{uuid4().hex[:8]}@mzk.cz",
        first_name="Test",
        last_name="Cataloguer",
        password_hash="x",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _decision(*candidates: Candidate) -> LinkDecision:
    return LinkDecision(
        accepted=candidates[0],
        candidates=list(candidates),
        candidate_count=len(candidates),
    )


def _write(db_session, record: CatalogRecord, decision: LinkDecision) -> None:
    handle_catalog_record_link_action(db_session, record, decision, TARGET_BASE)
    db_session.commit()


async def _pass(db_session, record: CatalogRecord, decision: LinkDecision) -> None:
    """One linking pass over one record, claims and all, as the worker runs it."""

    claims = LinkClaim.for_record(db_session, record.id, TARGET_BASE)
    decided, moved = await decide_with_claims(
        db_session, decision, claims, record.get_record(db_session), None
    )
    for claim in moved:
        claim.save(db_session, commit=False)
    _write(db_session, record, decided)


def _claim_row(db_session, record: CatalogRecord, sysno: str, verdict: ClaimVerdict) -> LinkClaim:
    claim = LinkClaim(
        main_record_id=record.id,
        base=TARGET_BASE,
        authority_base=TARGET_BASE,
        authority_sysno=sysno,
        verdict=verdict,
        claimed_by=_cataloguer(db_session).id,
        claimed_confidence=None,
        rival_confidence=None,
    )
    db_session.add(claim)
    db_session.commit()
    return claim


def _answer(db_session, record: CatalogRecord) -> AuthorityLink:
    return (
        db_session.query(AuthorityLink)
        .filter_by(main_record_id=record.id, base=TARGET_BASE, rank=ANSWER_RANK)
        .one()
    )


class TestAPassHonoursTheClaim:
    @pytest.mark.asyncio
    async def test_a_claimed_runner_up_becomes_the_answer(self, db_session):
        record = _record(db_session, "000000811")
        decision = _decision(_candidate("000000911", 13.0), _candidate("000000912", 12.5))
        _write(db_session, record, decision)
        _claim_row(db_session, record, "000000912", ClaimVerdict.SameWork)

        await _pass(db_session, record, decision)

        answer = _answer(db_session, record)
        assert answer.outcome == LinkOutcome.Linked
        assert answer.authority_sysno == "000000912"

    @pytest.mark.asyncio
    async def test_the_claim_still_wins_after_the_rival_improves(self, db_session):
        record = _record(db_session, "000000812")
        _write(db_session, record, _decision(_candidate("000000913", 13.0)))
        _claim_row(db_session, record, "000000914", ClaimVerdict.SameWork)

        # A later pass where the machine's favourite scores even better.
        await _pass(
            db_session,
            record,
            _decision(_candidate("000000913", 15.0), _candidate("000000914", 9.0)),
        )

        assert _answer(db_session, record).authority_sysno == "000000914"

    @pytest.mark.asyncio
    async def test_refusing_the_only_candidate_says_so_on_the_record(self, db_session):
        record = _record(db_session, "000000813")
        decision = _decision(_candidate("000000915", 13.0))
        _write(db_session, record, decision)
        _claim_row(db_session, record, "000000915", ClaimVerdict.NotSameWork)

        await _pass(db_session, record, decision)

        answer = _answer(db_session, record)
        assert answer.outcome == LinkOutcome.Refused
        assert answer.authority_record_id is None

    @pytest.mark.asyncio
    async def test_withdrawing_gives_the_linkers_their_answer_back(self, db_session):
        record = _record(db_session, "000000814")
        decision = _decision(_candidate("000000916", 13.0), _candidate("000000917", 12.5))
        _write(db_session, record, decision)
        claim = _claim_row(db_session, record, "000000917", ClaimVerdict.SameWork)
        await _pass(db_session, record, decision)
        assert _answer(db_session, record).authority_sysno == "000000917"

        db_session.delete(claim)
        db_session.commit()
        await _pass(db_session, record, decision)

        assert _answer(db_session, record).authority_sysno == "000000916"

    @pytest.mark.asyncio
    async def test_a_rival_pulling_ahead_raises_the_flag_without_moving_the_answer(
        self, db_session
    ):
        record = _record(db_session, "000000815")
        decision = _decision(_candidate("000000918", 13.0), _candidate("000000919", 12.5))
        _write(db_session, record, decision)
        claim = _claim_row(db_session, record, "000000919", ClaimVerdict.SameWork)
        claim.claimed_confidence = 12.5
        claim.rival_confidence = 13.0
        db_session.commit()

        await _pass(
            db_session,
            record,
            _decision(_candidate("000000918", 15.0), _candidate("000000919", 12.5)),
        )

        db_session.refresh(claim)
        assert claim.needs_review
        assert _answer(db_session, record).authority_sysno == "000000919"


class TestTheApiRecordsTheVerdictAndHandsOver:
    @pytest.mark.asyncio
    async def test_a_claim_remembers_the_gap_it_overruled(self, db_session, monkeypatch):
        record = _record(db_session, "000000821")
        _write(
            db_session,
            record,
            _decision(_candidate("000000921", 13.0), _candidate("000000922", 12.5)),
        )
        user = _cataloguer(db_session)
        monkeypatch.setattr(service, "_reapply", _noop)

        claim = await service.claim_link(
            record.id,
            LinkClaimRequest(
                base=TARGET_BASE,
                authority_base=TARGET_BASE,
                authority_sysno="000000922",
                verdict=ClaimVerdict.SameWork,
            ),
            str(user.id),
            db_session,
        )

        assert claim.claimed_confidence == 12.5
        assert claim.rival_confidence == 13.0
        assert not claim.needs_review

    @pytest.mark.asyncio
    async def test_a_second_verdict_replaces_the_first(self, db_session, monkeypatch):
        record = _record(db_session, "000000822")
        _write(
            db_session,
            record,
            _decision(
                _candidate("000000923", 13.0),
                _candidate("000000924", 12.5),
                _candidate("000000925", 12.4),
            ),
        )
        user = _cataloguer(db_session)
        monkeypatch.setattr(service, "_reapply", _noop)

        for sysno in ("000000924", "000000925"):
            await service.claim_link(
                record.id,
                LinkClaimRequest(
                    base=TARGET_BASE,
                    authority_base=TARGET_BASE,
                    authority_sysno=sysno,
                    verdict=ClaimVerdict.SameWork,
                ),
                str(user.id),
                db_session,
            )

        # A cataloguer cannot hold that two different records are both the
        # match, so the earlier verdict goes rather than competing.
        standing = LinkClaim.for_record(db_session, record.id, TARGET_BASE)
        assert [c.authority_sysno for c in standing if c.is_same_work] == ["000000925"]

    @pytest.mark.asyncio
    async def test_refusals_stack(self, db_session, monkeypatch):
        record = _record(db_session, "000000823")
        _write(
            db_session,
            record,
            _decision(_candidate("000000926", 13.0), _candidate("000000927", 12.5)),
        )
        user = _cataloguer(db_session)
        monkeypatch.setattr(service, "_reapply", _noop)

        for sysno in ("000000926", "000000927"):
            await service.claim_link(
                record.id,
                LinkClaimRequest(
                    base=TARGET_BASE,
                    authority_base=TARGET_BASE,
                    authority_sysno=sysno,
                    verdict=ClaimVerdict.NotSameWork,
                ),
                str(user.id),
                db_session,
            )

        standing = LinkClaim.for_record(db_session, record.id, TARGET_BASE)
        assert sorted(c.authority_sysno for c in standing) == ["000000926", "000000927"]


async def _noop(*args, **kwargs) -> None:
    """The hand-over, stubbed: enqueuing needs a broker these tests have not got."""

    return None

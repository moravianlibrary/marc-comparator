"""A record with no authority link should say why it has none.

The table used to hold one row per accepted link and nothing else, so every
other way of ending up unlinked — the lookup found nothing, the lookup never
completed — was stored as the absence of a row and read back as the same
thing. A link that vanished between passes was indistinguishable from one that
was never found, and a thousand failed lookups left the interface looking
exactly like a thousand records with no match in the union catalogue.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from marc_comparator.authority_linkers import MatchRoute

from authority_linking.tasks import (
    Candidate,
    LinkActionResult,
    LinkDecision,
    handle_catalog_record_link_action,
    record_lookup_failure,
    scenario_no_link_no_existing,
)
from catalog_records.models import RecordFilter
from catalog_records.search import build_filtered_query
from entities.authority_link import ANSWER_RANK, AuthorityLink, LinkOutcome
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from tests.conftest import load_test_record

pytestmark = pytest.mark.db

TARGET_BASE = "SKC"


def _record(
    db_session,
    system_number: str,
    base: str = "MZK01",
    source_type: CatalogRecordSource = CatalogRecordSource.Main,
) -> CatalogRecord:
    record = CatalogRecord(
        base=base,
        system_number=system_number,
        source_type=source_type,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def _link(db_session, main: CatalogRecord, authority: CatalogRecord, **kwargs) -> AuthorityLink:
    link = AuthorityLink(
        main_record_id=main.id,
        base=TARGET_BASE,
        rank=ANSWER_RANK,
        linker="marcxml-dump",
        outcome=LinkOutcome.Linked,
        authority_base=authority.base,
        authority_sysno=authority.system_number,
        authority_record_id=authority.id,
        confidence=0.95,
        matched_by=MatchRoute.Identifier.value,
        **kwargs,
    )
    db_session.add(link)
    db_session.commit()
    return link


def _answer(db_session, main: CatalogRecord) -> AuthorityLink | None:
    return AuthorityLink.find_answer(db_session, main.id, TARGET_BASE)


def _rows(db_session, main: CatalogRecord) -> list[AuthorityLink]:
    """This record's whole list for the target base, in rank order."""

    return (
        db_session.query(AuthorityLink)
        .filter_by(main_record_id=main.id, base=TARGET_BASE)
        .order_by(AuthorityLink.rank)
        .all()
    )


def _found_link(authority: CatalogRecord, confidence: float = 0.91) -> Any:
    """What a linker hands back, over a record the storage layer can write."""

    return SimpleNamespace(
        base=authority.base,
        system_number=authority.system_number,
        record=load_test_record("MZK01-001217709.mrc"),
        confidence=confidence,
        matched_by=MatchRoute.Identifier,
    )


def _linker_instance(name: str = "marcxml-dump") -> Any:
    return SimpleNamespace(linker=SimpleNamespace(value=name))


def _candidate(
    authority: CatalogRecord, confidence: float = 0.91, linker: str = "marcxml-dump"
) -> Candidate:
    return Candidate(_found_link(authority, confidence), _linker_instance(linker))


def _decision(*candidates: Candidate) -> LinkDecision:
    """A decision accepting the best of these candidates."""

    ordered = sorted(candidates, key=lambda c: c.link.confidence or 0.0, reverse=True)
    return LinkDecision(
        accepted=ordered[0] if ordered else None,
        candidates=ordered,
        candidate_count=len(ordered),
    )


def _rejected(*candidates: Candidate) -> LinkDecision:
    """Candidates were weighed and not one of them cleared a floor."""

    ordered = sorted(candidates, key=lambda c: c.link.confidence or 0.0, reverse=True)
    return LinkDecision(accepted=None, candidates=ordered, candidate_count=len(ordered))


class TestAGapIsWrittenWhereALinkWouldBe:
    def test_a_record_with_no_candidate_says_so(self, db_session):
        record = _record(db_session, "000000001")

        results = scenario_no_link_no_existing(db_session, record.id, TARGET_BASE)
        db_session.commit()

        assert results == [LinkActionResult.NoLinkFound]
        row = _answer(db_session, record)
        assert row is not None
        assert row.outcome == LinkOutcome.NoCandidate
        assert row.authority_record_id is None
        assert row.linker is None, "no single linker owns a silence that was unanimous"

    def test_the_record_is_still_not_linked(self, db_session):
        """The whole point of the guard: a gap row is not a link.

        Every reader that means "these two records are the same work" goes
        through the relationship or the finder below, and a `NoCandidate` row
        answering either of them would report a link to nothing.
        """

        record = _record(db_session, "000000002")
        scenario_no_link_no_existing(db_session, record.id, TARGET_BASE)
        db_session.commit()
        db_session.expire_all()

        record = cast(CatalogRecord, db_session.get(CatalogRecord, record.id))
        assert record.authority_links == []
        assert (
            AuthorityLink.find_by_main_record_and_base(db_session, record.id, TARGET_BASE) is None
        )
        assert len(record.link_attempts) == 1


class TestALinkThatDisappearsLeavesAReason:
    def test_the_link_becomes_a_gap_row(self, db_session):
        record = _record(db_session, "000000010")
        authority = _record(
            db_session,
            "000000011",
            base=TARGET_BASE,
            source_type=CatalogRecordSource.AuthorityLinker,
        )
        _link(db_session, record, authority)

        results = handle_catalog_record_link_action(
            db_session, record, LinkDecision.nothing_found(), TARGET_BASE
        )
        db_session.commit()

        assert results == [LinkActionResult.DeletedLink]
        row = _answer(db_session, record)
        assert row is not None
        assert row.outcome == LinkOutcome.NoCandidate
        assert row.authority_record_id is None
        assert row.confidence is None

    def test_the_authority_record_itself_is_left_alone(self, db_session):
        """Retracting a link is not a reason to drop the cached record."""

        record = _record(db_session, "000000012")
        authority = _record(
            db_session,
            "000000013",
            base=TARGET_BASE,
            source_type=CatalogRecordSource.AuthorityLinker,
        )
        _link(db_session, record, authority)

        handle_catalog_record_link_action(
            db_session, record, LinkDecision.nothing_found(), TARGET_BASE
        )
        db_session.commit()

        assert db_session.get(CatalogRecord, authority.id) is not None


class TestAFailedLookupIsNotAnAnswer:
    def test_it_is_recorded_with_its_reason(self, db_session):
        record = _record(db_session, "000000020")

        record_lookup_failure(db_session, record.id, TARGET_BASE, "the dump is not harvested")
        db_session.commit()

        row = _answer(db_session, record)
        assert row is not None
        assert row.outcome == LinkOutcome.LookupFailed
        assert row.detail == "the dump is not harvested"

    def test_it_does_not_overwrite_a_standing_link(self, db_session):
        """A lookup that failed says nothing about the record.

        Which is why the caller does not delete a link over one — and for the
        same reason this must not bury one either. The failure belongs in the
        log and the counters until there is somewhere it can go without
        contradicting something we do know.
        """

        record = _record(db_session, "000000021")
        authority = _record(
            db_session,
            "000000022",
            base=TARGET_BASE,
            source_type=CatalogRecordSource.AuthorityLinker,
        )
        _link(db_session, record, authority)

        record_lookup_failure(db_session, record.id, TARGET_BASE, "knihovny.cz timed out")
        db_session.commit()

        row = _answer(db_session, record)
        assert row is not None
        assert row.outcome == LinkOutcome.Linked
        assert row.authority_record_id == authority.id

    def test_it_replaces_an_earlier_gap_row(self, db_session):
        record = _record(db_session, "000000023")
        scenario_no_link_no_existing(db_session, record.id, TARGET_BASE)
        db_session.commit()

        record_lookup_failure(db_session, record.id, TARGET_BASE, "boom")
        db_session.commit()

        rows = db_session.query(AuthorityLink).filter_by(main_record_id=record.id).all()
        assert len(rows) == 1, "one answer per record and base, whatever it says"
        assert rows[0].outcome == LinkOutcome.LookupFailed


class TestALinkFoundLaterTakesTheSlotBack:
    def test_a_gap_row_does_not_block_the_link(self, db_session):
        """The reason the writer rewrites the row instead of replacing it.

        A gap row sits at exactly the key a new link wants, so inserting
        alongside it would collide; deleting it and inserting in the same flush
        would leave the order up to the unit of work rather than the code.
        """

        record = _record(db_session, "000000030")
        authority = _record(
            db_session,
            "000000031",
            base=TARGET_BASE,
            source_type=CatalogRecordSource.AuthorityLinker,
        )
        scenario_no_link_no_existing(db_session, record.id, TARGET_BASE)
        db_session.commit()

        results = handle_catalog_record_link_action(
            db_session, record, _decision(_candidate(authority)), TARGET_BASE
        )
        db_session.commit()
        db_session.expire_all()

        assert LinkActionResult.CreatedLink in results
        row = _answer(db_session, record)
        assert row is not None
        assert row.outcome == LinkOutcome.Linked
        assert row.authority_sysno == authority.system_number
        assert row.detail is None

        record = cast(CatalogRecord, db_session.get(CatalogRecord, record.id))
        assert [link.linked_record_id for link in record.authority_links] == [authority.id]


class TestTheGapIsFindable:
    def test_the_filter_selects_it(self, db_session):
        unlinked = _record(db_session, "000000040")
        linked = _record(db_session, "000000041")
        authority = _record(
            db_session,
            "000000042",
            base=TARGET_BASE,
            source_type=CatalogRecordSource.AuthorityLinker,
        )
        scenario_no_link_no_existing(db_session, unlinked.id, TARGET_BASE)
        _link(db_session, linked, authority)
        db_session.commit()

        found = build_filtered_query(
            db_session, RecordFilter(link_outcomes=[LinkOutcome.NoCandidate.value])
        ).all()

        assert [r.id for r in found] == [unlinked.id]

    def test_the_link_filters_do_not(self, db_session):
        """`authority_link_bases` means "linked to", and a gap is not a link."""

        unlinked = _record(db_session, "000000043")
        scenario_no_link_no_existing(db_session, unlinked.id, TARGET_BASE)
        db_session.commit()

        assert (
            build_filtered_query(db_session, RecordFilter(authority_link_bases=[TARGET_BASE])).all()
            == []
        )


class TestTheRunnerUpsAreKept:
    """What the record was nearly linked to, for whoever has to judge it.

    Every candidate was compared to pick the winner; the losing scores were
    thrown away afterwards. A cataloguer told "this is the match" and nothing
    else cannot see that the runner-up scored 0.99, which is exactly when they
    need to look — either the union catalogue holds a duplicate or we are
    about to pick the wrong one of a pair.
    """

    def test_a_doubtful_winner_keeps_its_alternatives(self, db_session):
        record = _record(db_session, "000000050")
        won = _record(db_session, "000000051", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        lost = _record(db_session, "000000052", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 0.71), _candidate(lost, 0.64)),
            TARGET_BASE,
        )
        db_session.commit()
        db_session.expire_all()

        rows = _rows(db_session, record)
        assert [(r.rank, r.outcome, r.authority_sysno) for r in rows] == [
            (0, LinkOutcome.Linked, won.system_number),
            (1, LinkOutcome.Rejected, lost.system_number),
        ]
        assert rows[1].authority_record_id is None, (
            "a candidate nobody accepted is not worth a persisted copy of the record"
        )
        assert rows[1].confidence == 0.64

    def test_a_confident_winner_keeps_a_near_tie(self, db_session):
        """Perfect and ambiguous at the same time is the case score alone misses."""

        record = _record(db_session, "000000053")
        won = _record(db_session, "000000054", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        lost = _record(db_session, "000000055", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 1.0), _candidate(lost, 0.99)),
            TARGET_BASE,
        )
        db_session.commit()

        assert [r.rank for r in _rows(db_session, record)] == [0, 1]

    def test_a_confident_winner_drops_a_distant_rival(self, db_session):
        record = _record(db_session, "000000056")
        won = _record(db_session, "000000057", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        lost = _record(db_session, "000000058", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 1.0), _candidate(lost, 0.40)),
            TARGET_BASE,
        )
        db_session.commit()

        rows = _rows(db_session, record)
        assert [r.rank for r in rows] == [0]
        assert rows[0].candidate_count == 2, (
            "the count is what says two were weighed when only one was kept"
        )

    def test_the_kept_list_is_replaced_not_appended(self, db_session):
        record = _record(db_session, "000000060")
        won = _record(db_session, "000000061", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        first = _record(db_session, "000000062", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        second = _record(db_session, "000000063", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 0.71), _candidate(first, 0.64)),
            TARGET_BASE,
        )
        db_session.commit()
        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 0.71), _candidate(second, 0.66)),
            TARGET_BASE,
        )
        db_session.commit()
        db_session.expire_all()

        rows = _rows(db_session, record)
        assert [r.authority_sysno for r in rows] == [won.system_number, second.system_number]

    def test_a_runner_up_can_become_the_answer(self, db_session):
        """The swap the rows are rewritten wholesale to survive.

        The record being promoted is in the table already, at another rank.
        Reconciling row by row would have it there twice before the flush
        that fixes it, and both the primary key and the candidate index
        refuse that.
        """

        record = _record(db_session, "000000070")
        first = _record(db_session, "000000071", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        second = _record(db_session, "000000072", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(first, 0.71), _candidate(second, 0.64)),
            TARGET_BASE,
        )
        db_session.commit()
        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(first, 0.64), _candidate(second, 0.71)),
            TARGET_BASE,
        )
        db_session.commit()
        db_session.expire_all()

        rows = _rows(db_session, record)
        assert [(r.rank, r.authority_sysno) for r in rows] == [
            (0, second.system_number),
            (1, first.system_number),
        ]
        assert rows[0].outcome == LinkOutcome.Linked


class TestNothingGoodEnoughIsStillAFinding:
    def test_the_best_rejected_candidate_is_named(self, db_session):
        """A floor set too high is invisible without this.

        The records it rejects would otherwise look exactly like the ones with
        no match in the union catalogue at all.
        """

        record = _record(db_session, "000000080")
        best = _record(db_session, "000000081", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        rest = _record(db_session, "000000082", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        results = handle_catalog_record_link_action(
            db_session,
            record,
            _rejected(_candidate(best, 0.42), _candidate(rest, 0.31)),
            TARGET_BASE,
        )
        db_session.commit()
        db_session.expire_all()

        assert results == [LinkActionResult.NoLinkFound]
        rows = _rows(db_session, record)
        assert rows[0].outcome == LinkOutcome.BelowFloor
        assert rows[0].authority_sysno == best.system_number
        assert rows[0].confidence == 0.42
        assert rows[0].candidate_count == 2
        assert rows[0].authority_record_id is None, "refused is not linked"

    def test_it_is_not_a_link(self, db_session):
        record = _record(db_session, "000000083")
        best = _record(db_session, "000000084", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session, record, _rejected(_candidate(best, 0.42)), TARGET_BASE
        )
        db_session.commit()
        db_session.expire_all()

        record = cast(CatalogRecord, db_session.get(CatalogRecord, record.id))
        assert record.authority_links == []
        assert build_filtered_query(
            db_session, RecordFilter(link_outcomes=[LinkOutcome.BelowFloor.value])
        ).all() == [record]

    def test_the_whole_shortlist_is_kept(self, db_session):
        """Pruning the evidence would leave a refusal with nothing behind it."""

        record = _record(db_session, "000000085")
        best = _record(db_session, "000000086", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        rest = _record(db_session, "000000087", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _rejected(_candidate(best, 0.42), _candidate(rest, 0.05)),
            TARGET_BASE,
        )
        db_session.commit()
        db_session.expire_all()

        rows = _rows(db_session, record)
        assert [(r.rank, r.outcome) for r in rows] == [
            (0, LinkOutcome.BelowFloor),
            (1, LinkOutcome.Rejected),
        ]

    def test_a_link_found_later_clears_the_refusal(self, db_session):
        record = _record(db_session, "000000088")
        candidate = _record(
            db_session, "000000089", TARGET_BASE, CatalogRecordSource.AuthorityLinker
        )

        handle_catalog_record_link_action(
            db_session, record, _rejected(_candidate(candidate, 0.42)), TARGET_BASE
        )
        db_session.commit()
        handle_catalog_record_link_action(
            db_session, record, _decision(_candidate(candidate, 0.95)), TARGET_BASE
        )
        db_session.commit()
        db_session.expire_all()

        rows = _rows(db_session, record)
        assert [(r.rank, r.outcome) for r in rows] == [(0, LinkOutcome.Linked)]
        assert rows[0].authority_record_id == candidate.id


class TestTheSummaryCarriesTheWholeStory:
    """What the interface needs to show a cataloguer more than a bare answer."""

    def _summary(self, db_session, record: CatalogRecord):
        from catalog_records.models import SearchRecordsRequest
        from catalog_records.search import search_records

        response = search_records(
            SearchRecordsRequest(filters=RecordFilter(record_ids=[record.id])), db_session
        )
        return response.items[0]

    def test_a_gap_is_reported_as_an_attempt_and_not_as_a_link(self, db_session):
        record = _record(db_session, "000000090")
        scenario_no_link_no_existing(db_session, record.id, TARGET_BASE)
        db_session.commit()

        summary = self._summary(db_session, record)

        assert summary.authority_links == []
        assert [(a.rank, a.outcome) for a in summary.link_attempts] == [
            (0, LinkOutcome.NoCandidate)
        ]
        assert summary.link_attempts[0].linker is None

    def test_a_failed_lookup_carries_its_reason(self, db_session):
        record = _record(db_session, "000000091")
        record_lookup_failure(db_session, record.id, TARGET_BASE, "knihovny.cz timed out")
        db_session.commit()

        attempt = self._summary(db_session, record).link_attempts[0]

        assert attempt.outcome == LinkOutcome.LookupFailed
        assert attempt.detail == "knihovny.cz timed out"

    def test_an_accepted_link_appears_in_both_lists(self, db_session):
        """Once as the link it is, once as the first step of how it was chosen."""

        record = _record(db_session, "000000092")
        won = _record(db_session, "000000093", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        lost = _record(db_session, "000000094", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 0.71), _candidate(lost, 0.64)),
            TARGET_BASE,
        )
        db_session.commit()

        summary = self._summary(db_session, record)

        assert [link.authority_record_id for link in summary.authority_links] == [won.id]
        assert [(a.rank, a.outcome, a.authority_sysno) for a in summary.link_attempts] == [
            (0, LinkOutcome.Linked, won.system_number),
            (1, LinkOutcome.Rejected, lost.system_number),
        ]
        assert summary.link_attempts[0].candidate_count == 2
        assert summary.link_attempts[1].authority_record_id is None

    def test_a_broken_record_says_what_broke(self, db_session):
        """The message was in the API and unread; a Broken badge alone is not
        something anybody can act on."""

        record = _record(db_session, "000000095")
        record.processing_error = "variable_fields.500.0.ind1"
        db_session.commit()

        assert self._summary(db_session, record).processing_error == ("variable_fields.500.0.ind1")

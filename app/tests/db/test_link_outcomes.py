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

from adapters.marc_sectors import marc_bytes_of, read_marc
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
from entities.marc_sector import MarcRecordIndex
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
        confidence=14.0,
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


def _found_link(
    authority: CatalogRecord, confidence: float = 12.5, conflicts: list[Any] | None = None
) -> Any:
    """What a linker hands back, over a record the storage layer can write."""

    return SimpleNamespace(
        base=authority.base,
        system_number=authority.system_number,
        record=load_test_record("MZK01-001217709.mrc"),
        confidence=confidence,
        matched_by=MatchRoute.Identifier,
        conflicts=conflicts or [],
    )


def _linker_name(name: str | None = "marcxml-dump") -> str | None:
    """A candidate carries the name of what proposed it, or nothing.

    Nothing is a real case: a cataloguer's claim can put a record in front of
    the pipeline that no linker returned.
    """

    return name


def _candidate(
    authority: CatalogRecord, confidence: float = 12.5, linker: str = "marcxml-dump"
) -> Candidate:
    return Candidate(_found_link(authority, confidence), _linker_name(linker))


def _bare_candidate(system_number: str, confidence: float = 12.5) -> Candidate:
    """A candidate our catalogue has never heard of, which is the usual case.

    Every other helper here builds its candidates out of records that already
    exist, because those tests are about the link rows. These ones are about
    what we hold of the record itself, and holding it must not depend on
    having a catalogue row for it.
    """

    link = SimpleNamespace(
        base=TARGET_BASE,
        system_number=system_number,
        record=load_test_record("MZK01-001217709.mrc"),
        confidence=confidence,
        matched_by=MatchRoute.Identifier,
    )
    return Candidate(cast(Any, link), _linker_name())


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
    else cannot see that the runner-up scored 14.9, which is exactly when they
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
            _decision(_candidate(won, 10.5), _candidate(lost, 9.5)),
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
        assert rows[1].confidence == 9.5

    def test_a_confident_winner_keeps_a_near_tie(self, db_session):
        """Perfect and ambiguous at the same time is the case score alone misses."""

        record = _record(db_session, "000000053")
        won = _record(db_session, "000000054", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        lost = _record(db_session, "000000055", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 15.0), _candidate(lost, 14.9)),
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
            _decision(_candidate(won, 15.0), _candidate(lost, 5.0)),
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
            _decision(_candidate(won, 10.5), _candidate(first, 9.5)),
            TARGET_BASE,
        )
        db_session.commit()
        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 10.5), _candidate(second, 10.0)),
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
            _decision(_candidate(first, 10.5), _candidate(second, 9.5)),
            TARGET_BASE,
        )
        db_session.commit()
        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(first, 9.5), _candidate(second, 10.5)),
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
            _rejected(_candidate(best, 6.0), _candidate(rest, 4.5)),
            TARGET_BASE,
        )
        db_session.commit()
        db_session.expire_all()

        assert results == [LinkActionResult.NoLinkFound]
        rows = _rows(db_session, record)
        assert rows[0].outcome == LinkOutcome.BelowFloor
        assert rows[0].authority_sysno == best.system_number
        assert rows[0].confidence == 6.0
        assert rows[0].candidate_count == 2
        assert rows[0].authority_record_id is None, "refused is not linked"

    def test_it_is_not_a_link(self, db_session):
        record = _record(db_session, "000000083")
        best = _record(db_session, "000000084", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session, record, _rejected(_candidate(best, 6.0)), TARGET_BASE
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
            _rejected(_candidate(best, 6.0), _candidate(rest, 0.75)),
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
            db_session, record, _rejected(_candidate(candidate, 6.0)), TARGET_BASE
        )
        db_session.commit()
        handle_catalog_record_link_action(
            db_session, record, _decision(_candidate(candidate, 14.0)), TARGET_BASE
        )
        db_session.commit()
        db_session.expire_all()

        rows = _rows(db_session, record)
        assert [(r.rank, r.outcome) for r in rows] == [(0, LinkOutcome.Linked)]
        assert rows[0].authority_record_id == candidate.id


class TestARefusalOnEvidenceIsNotARefusalOnScore:
    """A low score invites a look; a contradiction says stop looking.

    Measured over 47,777 links, 90 carried a conflicting identifier and 78 of
    those agreed on a different one. Reading them by hand the national
    bibliography number was right every time — so the veto outranks both the
    score and the identifier that retrieved the pair, and the row has to say
    which rule refused it or a rule set too strict is invisible.
    """

    def _refused(self, db_session, record: CatalogRecord, *candidates: Candidate):
        handle_catalog_record_link_action(db_session, record, _rejected(*candidates), TARGET_BASE)
        db_session.commit()
        db_session.expire_all()
        return _rows(db_session, record)

    def test_a_conflicting_candidate_says_so(self, db_session):
        record = _record(db_session, "000000300")
        other = _record(db_session, "000000301", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        rows = self._refused(
            db_session,
            record,
            Candidate(_found_link(other, 6.0, ["nbn"]), _linker_name()),
        )

        assert rows[0].outcome == LinkOutcome.Conflicting
        assert rows[0].detail == "nbn"
        assert rows[0].authority_sysno == other.system_number, "name what was refused"
        assert rows[0].authority_record_id is None, "refused is not linked"

    def test_every_reason_reaches_the_row(self, db_session):
        record = _record(db_session, "000000302")
        other = _record(db_session, "000000303", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        rows = self._refused(
            db_session,
            record,
            Candidate(_found_link(other, 6.0, ["nbn", "year"]), _linker_name()),
        )

        assert rows[0].detail == "nbn, year"

    def test_a_weak_candidate_is_still_only_weak(self, db_session):
        """Nothing disqualified it, so it stays the invitation to look it up."""

        record = _record(db_session, "000000304")
        other = _record(db_session, "000000305", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        rows = self._refused(db_session, record, _candidate(other, 6.0))

        assert rows[0].outcome == LinkOutcome.BelowFloor
        assert rows[0].detail is None

    def test_the_two_refusals_are_separate_buckets(self, db_session):
        conflicting = _record(db_session, "000000306")
        weak = _record(db_session, "000000307")
        a = _record(db_session, "000000308", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        b = _record(db_session, "000000309", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        self._refused(
            db_session, conflicting, Candidate(_found_link(a, 6.0, ["nbn"]), _linker_name())
        )
        self._refused(db_session, weak, _candidate(b, 6.0))

        assert build_filtered_query(
            db_session, RecordFilter(link_outcomes=[LinkOutcome.Conflicting.value])
        ).all() == [conflicting]
        assert build_filtered_query(
            db_session, RecordFilter(link_outcomes=[LinkOutcome.BelowFloor.value])
        ).all() == [weak]

    def test_a_link_found_later_clears_the_contradiction(self, db_session):
        record = _record(db_session, "000000310")
        other = _record(db_session, "000000311", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        self._refused(
            db_session, record, Candidate(_found_link(other, 6.0, ["nbn"]), _linker_name())
        )
        handle_catalog_record_link_action(
            db_session, record, _decision(_candidate(other, 14.0)), TARGET_BASE
        )
        db_session.commit()
        db_session.expire_all()

        rows = _rows(db_session, record)
        assert [(r.rank, r.outcome) for r in rows] == [(0, LinkOutcome.Linked)]
        assert rows[0].detail is None


class TestTheCandidateMarcIsOurs:
    """A candidate row must not be a pointer into a plugin's tables.

    The linker that proposes a candidate holds the union catalogue in a schema
    it owns and is free to re-harvest, rebuild or drop. A row saying "this
    record was nearly linked to SKC 123456" outlives that, and is worth
    nothing if the only copy of SKC 123456 went with the harvest.

    So the MARC goes into our own sector store, which is keyed by base and
    system number and has no foreign key to the catalogue — the candidate
    stays cheap, and what it refers to is ours.
    """

    def _stored(self, db_session, system_number: str) -> bytes | None:
        return read_marc(db_session, TARGET_BASE, system_number)

    def test_a_kept_runner_up_leaves_its_marc_behind(self, db_session):
        record = _record(db_session, "000000200")

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_bare_candidate("000000201", 14.0), _bare_candidate("000000202", 13.0)),
            TARGET_BASE,
        )
        db_session.commit()

        assert self._stored(db_session, "000000202") == marc_bytes_of(
            load_test_record("MZK01-001217709.mrc")
        )

    def test_it_is_still_not_a_record_in_our_catalogue(self, db_session):
        """Cheap for the reason it always was: no catalogue row, no search text."""

        record = _record(db_session, "000000203")

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_bare_candidate("000000204", 14.0), _bare_candidate("000000205", 13.0)),
            TARGET_BASE,
        )
        db_session.commit()
        db_session.expire_all()

        assert (
            CatalogRecord.find_by_base_and_system_number(db_session, TARGET_BASE, "000000205")
            is None
        )
        rows = _rows(db_session, record)
        assert [(r.rank, r.authority_sysno, r.authority_record_id) for r in rows] == [
            (0, "000000204", f"{TARGET_BASE}-000000204"),
            (1, "000000205", None),
        ]

    def test_a_candidate_not_worth_keeping_is_not_worth_storing(self, db_session):
        """The union catalogue is nine million records; we keep what we show."""

        record = _record(db_session, "000000206")

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_bare_candidate("000000207", 14.0), _bare_candidate("000000208", 5.0)),
            TARGET_BASE,
        )
        db_session.commit()

        assert [r.rank for r in _rows(db_session, record)] == [ANSWER_RANK]
        assert self._stored(db_session, "000000208") is None

    def test_the_record_that_missed_its_floor_is_kept_too(self, db_session):
        """It sits at the answer rank, but it is a candidate like any other."""

        record = _record(db_session, "000000209")

        handle_catalog_record_link_action(
            db_session,
            record,
            _rejected(_bare_candidate("000000210", 6.0), _bare_candidate("000000211", 4.5)),
            TARGET_BASE,
        )
        db_session.commit()

        assert self._stored(db_session, "000000210") is not None
        assert self._stored(db_session, "000000211") is not None

    def test_a_candidate_stored_without_its_marc_heals_on_the_next_pass(self, db_session):
        """Rows written before this existed, and any other way one goes missing.

        The MARC is written every pass rather than only when the rows change,
        because the store is keyed by the record and re-storing an unchanged
        one costs nothing.
        """

        record = _record(db_session, "000000212")
        decision = _decision(_bare_candidate("000000213", 14.0), _bare_candidate("000000214", 13.0))

        handle_catalog_record_link_action(db_session, record, decision, TARGET_BASE)
        db_session.commit()

        db_session.query(MarcRecordIndex).filter_by(
            base=TARGET_BASE, system_number="000000214"
        ).delete()
        db_session.commit()
        assert self._stored(db_session, "000000214") is None

        handle_catalog_record_link_action(db_session, record, decision, TARGET_BASE)
        db_session.commit()

        assert self._stored(db_session, "000000214") is not None


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
            _decision(_candidate(won, 10.5), _candidate(lost, 9.5)),
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


class TestTheOutcomeFacetPartitionsTheRecords:
    """`link_outcomes` is the answer for each base, not every row.

    A runner-up is not an outcome. Counting the `Rejected` rows here would
    put a value in the facet meaning "this record has stored alternatives",
    which is a different question, and the buckets would stop adding up to
    the records.
    """

    def _analytics(self, db_session, record: CatalogRecord):
        from sqlalchemy import text

        from catalog_records.analytics import TABLE, upsert_records

        upsert_records(db_session, [record.id])
        return db_session.execute(
            text(f"SELECT link_outcomes FROM {TABLE} WHERE id = :i"), {"i": record.id}
        ).scalar()

    def test_a_kept_runner_up_does_not_become_an_outcome(self, db_session):
        record = _record(db_session, "000000100")
        won = _record(db_session, "000000101", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        lost = _record(db_session, "000000102", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 10.5), _candidate(lost, 9.5)),
            TARGET_BASE,
        )
        db_session.commit()

        assert self._analytics(db_session, record) == ["Linked"]

    def test_the_filter_agrees_with_the_facet(self, db_session):
        """The ORM and the analytics compiler answer the same question."""

        record = _record(db_session, "000000103")
        won = _record(db_session, "000000104", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        lost = _record(db_session, "000000105", TARGET_BASE, CatalogRecordSource.AuthorityLinker)

        handle_catalog_record_link_action(
            db_session,
            record,
            _decision(_candidate(won, 10.5), _candidate(lost, 9.5)),
            TARGET_BASE,
        )
        db_session.commit()

        assert (
            build_filtered_query(
                db_session, RecordFilter(link_outcomes=[LinkOutcome.Rejected.value])
            ).all()
            == []
        )
        assert build_filtered_query(
            db_session, RecordFilter(link_outcomes=[LinkOutcome.Linked.value])
        ).all() == [record]


class TestWhoCataloguedTheOtherRecord:
    """A third of our links point at a record MZK itself catalogued.

    14,230 of 47,777, and 12,624 of those score exactly 1.00 — 52% of the
    whole perfect-score population. For those the comparison is our record
    against the copy we contributed to the union catalogue, so there is no
    second opinion in it and nothing to report to anyone. Without a way to
    see them the review queue is 30% larger than it needs to be.
    """

    def _linked_to(self, db_session, main: CatalogRecord, agency: str | None) -> CatalogRecord:
        authority = _record(
            db_session,
            main.system_number + "9",
            TARGET_BASE,
            CatalogRecordSource.AuthorityLinker,
        )
        authority.cataloguing_agency = agency
        _link(db_session, main, authority)
        db_session.commit()
        db_session.expire_all()
        return authority

    def test_the_agency_is_read_off_the_record(self, db_session):
        """040 $a, which is in the comparator's IGNORE_TAG_PATTERNS.

        It cannot have influenced any score, which is exactly what makes it
        usable as a signal about the scores.
        """

        record = _record(db_session, "000000400")
        record.update_search_text_from(load_test_record("MZK01-001217709.mrc"))

        assert record.cataloguing_agency == "OLA001"

    def test_records_are_findable_by_who_catalogued_their_counterpart(self, db_session):
        ours = _record(db_session, "000000401")
        theirs = _record(db_session, "000000402")
        self._linked_to(db_session, ours, "BOA001")
        self._linked_to(db_session, theirs, "ABA001")

        assert build_filtered_query(db_session, RecordFilter(link_agencies=["ABA001"])).all() == [
            theirs
        ]
        assert build_filtered_query(db_session, RecordFilter(link_agencies=["BOA001"])).all() == [
            ours
        ]

    def test_a_refused_candidate_is_not_somebody_we_linked_to(self, db_session):
        """The question is who catalogued what we linked to, not what we saw."""

        record = _record(db_session, "000000403")
        refused = _record(db_session, "000000404", TARGET_BASE, CatalogRecordSource.AuthorityLinker)
        refused.cataloguing_agency = "ABA001"
        handle_catalog_record_link_action(
            db_session, record, _rejected(_candidate(refused, 6.0)), TARGET_BASE
        )
        db_session.commit()
        db_session.expire_all()

        assert build_filtered_query(db_session, RecordFilter(link_agencies=["ABA001"])).all() == []

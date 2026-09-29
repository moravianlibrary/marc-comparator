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
    LinkActionResult,
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


def _found_link(authority: CatalogRecord) -> Any:
    """What a linker hands back, over a record the storage layer can write."""

    return SimpleNamespace(
        base=authority.base,
        system_number=authority.system_number,
        record=load_test_record("MZK01-001217709.mrc"),
        confidence=0.91,
        matched_by=MatchRoute.Identifier,
    )


def _linker_instance() -> Any:
    return SimpleNamespace(linker=SimpleNamespace(value="marcxml-dump"))


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

        results = handle_catalog_record_link_action(db_session, record, None, None, TARGET_BASE)
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

        handle_catalog_record_link_action(db_session, record, None, None, TARGET_BASE)
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

        found = _found_link(authority)
        linker = _linker_instance()

        results = handle_catalog_record_link_action(db_session, record, found, linker, TARGET_BASE)
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

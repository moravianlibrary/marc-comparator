"""A record nobody could read should say so, and stop looking clean.

A record whose MARC will not parse produces no comparisons and no validations
and never gets stamped. That made it read two ways, both wrong: Unprocessed,
which says only that no pass has reached it yet, and — because it has no results
to review — ReviewNotNeeded, which put it in the interface looking finished.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from authority_linking.tasks import AuthorityLinkingFailed
from catalog_records.filter_spec import parse_filters
from catalog_records.models import RecordFilter
from catalog_records.search import build_filtered_query
from catalog_records.tasks import (
    _PROCESSING_ERROR_LIMIT,
    _remember_processing_error,
    _settle_window,
)
from entities.catalog_record import (
    CatalogRecord,
    CatalogRecordSource,
    CatalogRecordState,
)

pytestmark = pytest.mark.db


def _record(db_session, system_number: str, **kwargs) -> CatalogRecord:
    record = CatalogRecord(
        base="MZK01",
        system_number=system_number,
        source_type=CatalogRecordSource.Main,
        **kwargs,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


class TestState:
    def test_a_broken_record_says_it_is_broken(self, db_session):
        record = _record(db_session, "000000001", processing_error="variable_fields.500.0.ind1")

        assert CatalogRecordState.Broken in record.state

    def test_a_broken_record_no_longer_claims_it_needs_no_review(self, db_session):
        """The reading that made this invisible.

        Every review state is derived from comparisons and validations, and a
        broken record has neither — so the "nothing to review" branch caught it
        and it sat in the interface indistinguishable from a clean record.
        """

        record = _record(db_session, "000000002", processing_error="will not decode")

        assert CatalogRecordState.ReviewNotNeeded not in record.state
        assert not {
            CatalogRecordState.Reviewed,
            CatalogRecordState.PartiallyReviewed,
            CatalogRecordState.Unreviewed,
        } & set(record.state)

    def test_it_is_still_reported_as_unprocessed(self, db_session):
        # True, and worth keeping: it has never been through a pass.
        record = _record(db_session, "000000003", processing_error="will not decode")

        assert CatalogRecordState.Unprocessed in record.state

    def test_a_readable_record_is_unaffected(self, db_session):
        record = _record(db_session, "000000004")

        assert CatalogRecordState.Broken not in record.state
        assert CatalogRecordState.ReviewNotNeeded in record.state


class TestFiltering:
    def test_broken_records_can_be_found(self, db_session):
        broken = _record(db_session, "000000010", processing_error="will not decode")
        _record(db_session, "000000011")

        found = build_filtered_query(db_session, RecordFilter(broken=True)).all()

        assert [r.id for r in found] == [broken.id]

    def test_readable_records_can_be_asked_for_too(self, db_session):
        _record(db_session, "000000012", processing_error="will not decode")
        readable = _record(db_session, "000000013")

        found = build_filtered_query(db_session, RecordFilter(broken=False)).all()

        assert [r.id for r in found] == [readable.id]

    def test_not_asking_selects_both(self, db_session):
        _record(db_session, "000000014", processing_error="will not decode")
        _record(db_session, "000000015")

        assert len(build_filtered_query(db_session, RecordFilter()).all()) == 2

    def test_broken_is_not_the_same_question_as_processed(self):
        # Both are false for a broken record, so a filter on one cannot stand
        # in for the other: "not reached yet" and "cannot be read" are
        # different work items.
        assert len(parse_filters(RecordFilter(broken=True, processed=False))) == 2


class TestRecordingAndClearing:
    def test_the_reason_is_written_on_the_record(self, db_session):
        record = _record(db_session, "000000020")
        ctx = cast(Any, SimpleNamespace(db_session=db_session))

        _remember_processing_error(ctx, record.id, "variable_fields.500.0.ind1: bad indicator")

        db_session.refresh(record)
        assert record.processing_error is not None
        assert "ind1" in record.processing_error

    def test_a_very_long_reason_is_cut_to_fit(self, db_session):
        record = _record(db_session, "000000021")
        ctx = cast(Any, SimpleNamespace(db_session=db_session))

        _remember_processing_error(ctx, record.id, "x" * (_PROCESSING_ERROR_LIMIT * 3))

        db_session.refresh(record)
        assert record.processing_error is not None
        assert len(record.processing_error) == _PROCESSING_ERROR_LIMIT

    def test_a_record_that_vanished_is_not_an_error(self, db_session):
        ctx = cast(Any, SimpleNamespace(db_session=db_session))

        _remember_processing_error(ctx, "MZK01-999999999", "gone")

    def test_getting_through_the_record_clears_it(self, db_session):
        """And stamps it, which nothing else here would.

        A record that was broken produced no results, so there are none to have
        changed — without treating recovery as a change of its own it would
        clear the error and still read as never processed.
        """

        record = _record(db_session, "000000022", processing_error="will not decode")
        ctx = cast(Any, SimpleNamespace(db_session=db_session))

        _settle_window(ctx, [(record.id, {}, "")], {record.id: ""})
        db_session.commit()

        db_session.refresh(record)
        assert record.processing_error is None
        assert record.processed_at is not None
        assert CatalogRecordState.Broken not in record.state


def test_a_failed_lookup_is_not_a_broken_record():
    """The two failures are caught by different handlers, in that order.

    AuthorityLinkingFailed means an external lookup did not complete, not that
    the record is unreadable. If it were a ValueError it would fall into the
    branch that marks records broken, and every linker outage would blame the
    records it touched — which the next pass would then "repair", saying
    nothing about any of them.
    """

    assert not issubclass(AuthorityLinkingFailed, ValueError)

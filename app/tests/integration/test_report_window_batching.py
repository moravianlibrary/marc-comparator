"""A report reads its window in batches, not one record at a time.

Read per record, a validator report costs four queries each: the row, its
validations, and two more to locate and decompress the MARC. A comparator
report costs one. Neither scales, and a report covers whatever the filter
matched — which can be the whole catalogue.
"""

import pytest
from marc_comparator.validators import (
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)
from sqlalchemy import event

from adapters.database import DatabaseSession
from adapters.marc_sectors import read_marc_for_ids
from entities.comparison import Comparison
from entities.validation import Validation
from reports.tasks import _comparison_inputs_for, _failing_results_for
from tests.conftest import create_catalog_record, load_test_record

WINDOW = 12
TOOL = "kramerius-links"


def _result(status: ValidityStatus) -> dict:
    return ValidationResult(
        target=ValidationTarget(tag="856", codes=["u"]),
        status=status,
        reason="fixture",
    ).model_dump()


class _CountSelects:
    """Counts SELECTs issued while it is active."""

    def __init__(self, db_session: DatabaseSession):
        self._bind = db_session.get_bind()
        self.statements: list[str] = []

    @property
    def count(self) -> int:
        return len(self.statements)

    def __enter__(self):
        event.listen(self._bind, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *_):
        event.remove(self._bind, "before_cursor_execute", self._on_execute)
        return False

    def _on_execute(self, _conn, _cursor, statement, *_args):
        collapsed = " ".join(statement.split()).lower()
        if collapsed.startswith("select"):
            self.statements.append(collapsed[:140])


@pytest.fixture
def reported_window(db_session: DatabaseSession, marc_cache_client) -> list[str]:
    """A window of records sharing one sector, each with results to report."""
    marc_record = load_test_record("MZK01-001217709.mrc")
    ids = []
    for offset in range(WINDOW):
        record = create_catalog_record(db_session, "MZK01", f"00070{offset:04d}", marc_record)
        db_session.add(
            Validation(
                catalog_record_id=record.id,
                validator=TOOL,
                result=_result(ValidityStatus.Invalid),
            )
        )
        db_session.add(
            Comparison(
                main_record_id=record.id,
                comparator="default",
                base="SKC",
                other_record_id=record.id,
                result={"overall_score": 0.5},
            )
        )
        ids.append(record.id)
    db_session.commit()
    # A window read after a write must not be served from a cache the write
    # populated, or the test measures nothing.
    marc_cache_client.flushdb()
    return ids


@pytest.mark.db
@pytest.mark.redis
class TestTheValidatorReportReadsItsWindowInBatches:
    def test_a_window_costs_a_handful_of_queries(self, db_session, reported_window):
        with _CountSelects(db_session) as counted:
            failing = _failing_results_for(db_session, reported_window, TOOL)
            marc_by_id = read_marc_for_ids(db_session, list(failing))

        assert set(failing) == set(reported_window), "every record must bring its results"
        assert set(marc_by_id) == set(reported_window), "every record must bring its MARC"
        # The validations, the identity/base/system number, the index rows and
        # the one sector they share. Per record it would be four times WINDOW.
        assert counted.count <= 4, (
            f"{counted.count} SELECTs for {WINDOW} records — the window is not batched:\n"
            + "\n".join(counted.statements)
        )

    def test_only_the_failing_results_of_the_named_validator_come_back(
        self, db_session, reported_window
    ):
        """The report is of what is wrong, as judged by one tool."""
        record_id = reported_window[0]
        db_session.add_all(
            [
                Validation(
                    catalog_record_id=record_id,
                    validator=TOOL,
                    result=_result(ValidityStatus.Valid),
                ),
                Validation(
                    catalog_record_id=record_id,
                    validator="some-other-validator",
                    result=_result(ValidityStatus.Invalid),
                ),
            ]
        )
        db_session.commit()

        failing = _failing_results_for(db_session, reported_window, TOOL)

        assert [r.status for r in failing[record_id]] == [ValidityStatus.Invalid], (
            "a passing result, or another tool's, has no place in this report"
        )

    def test_an_empty_window_asks_nothing(self, db_session):
        with _CountSelects(db_session) as counted:
            assert _failing_results_for(db_session, [], TOOL) == {}
        assert counted.count == 0


@pytest.mark.db
@pytest.mark.redis
class TestTheComparatorReportReadsItsWindowInBatches:
    def test_a_window_costs_one_query(self, db_session, reported_window):
        with _CountSelects(db_session) as counted:
            stored = _comparison_inputs_for(db_session, reported_window, "default")

        assert set(stored) == set(reported_window)
        assert counted.count == 1, (
            f"{counted.count} SELECTs for {WINDOW} records — the window is not batched:\n"
            + "\n".join(counted.statements)
        )

    def test_the_inputs_survive_their_session(self, db_session, reported_window):
        """The caller cycles its session mid-window; rows would detach, these must not."""
        stored = _comparison_inputs_for(db_session, reported_window, "default")
        db_session.expunge_all()
        db_session.close()

        built = stored[reported_window[0]][0]
        assert built.base == "SKC"
        assert built.result.overall_score == 0.5

    def test_an_empty_window_asks_nothing(self, db_session):
        with _CountSelects(db_session) as counted:
            assert _comparison_inputs_for(db_session, [], "default") == {}
        assert counted.count == 0

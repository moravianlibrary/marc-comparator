"""Work already done must not be done again.

Both of these were found by profiling a pass over records where nothing had
changed: it deleted and rewrote every validation, and it fetched every record
one at a time although the window it belongs to had just been read.
"""

import pytest
from marc_comparator.validators import ValidationResult, ValidationTarget, ValidityStatus
from sqlalchemy import event

from adapters.database import DatabaseSession
from entities.catalog_record import CatalogRecord
from entities.validation import Validation
from tests.conftest import create_catalog_record, load_test_record


class _CountStatements:
    def __init__(self, db_session: DatabaseSession, *prefixes: str):
        self._bind = db_session.get_bind()
        self._prefixes = prefixes or ("select", "insert", "update", "delete")
        self.statements: list[str] = []

    @property
    def count(self) -> int:
        return len(self.statements)

    def of(self, prefix: str) -> int:
        return sum(1 for s in self.statements if s.startswith(prefix))

    def __enter__(self):
        event.listen(self._bind, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *_):
        event.remove(self._bind, "before_cursor_execute", self._on_execute)
        return False

    def _on_execute(self, _conn, _cursor, statement, *_args):
        collapsed = " ".join(statement.split()).lower()
        if collapsed.startswith(self._prefixes):
            self.statements.append(collapsed[:140])


def _result(reason: str, field_index: int = 0) -> ValidationResult:
    return ValidationResult(
        target=ValidationTarget(tag="856", codes=["u"], field_index=field_index),
        status=ValidityStatus.Invalid,
        reason=reason,
    )


@pytest.mark.db
@pytest.mark.redis
class TestValidationsAreNotRewrittenUnchanged:
    @pytest.fixture
    def record(self, db_session, marc_cache_client) -> CatalogRecord:
        record = create_catalog_record(
            db_session, "MZK01", "000700001", load_test_record("MZK01-001217709.mrc")
        )
        db_session.commit()
        return record

    def test_the_same_results_are_left_alone(self, db_session, record):
        results = [_result("missing"), _result("unreachable")]
        assert Validation.replace_all(db_session, record.id, "kramerius-links", results) is True
        db_session.commit()

        with _CountStatements(db_session, "insert", "update", "delete") as counted:
            written = Validation.replace_all(db_session, record.id, "kramerius-links", results)

        assert written is False
        assert counted.count == 0, "rewrote validations that had not changed:\n" + "\n".join(
            counted.statements
        )

    def test_order_from_the_database_is_not_a_change(self, db_session, record):
        """Stored rows come back in whatever order; that is not new information."""
        results = [_result("a"), _result("b"), _result("c")]
        Validation.replace_all(db_session, record.id, "kramerius-links", results)
        db_session.commit()

        assert (
            Validation.replace_all(
                db_session, record.id, "kramerius-links", list(reversed(results))
            )
            is False
        )

    def test_a_real_change_is_still_written(self, db_session, record):
        Validation.replace_all(db_session, record.id, "kramerius-links", [_result("missing")])
        db_session.commit()

        assert (
            Validation.replace_all(db_session, record.id, "kramerius-links", [_result("moved")])
            is True
        )
        db_session.commit()

        stored = (
            db_session.query(Validation)
            .filter_by(catalog_record_id=record.id, validator="kramerius-links")
            .all()
        )
        assert [row.reason for row in stored] == ["moved"]

    def test_results_going_away_is_a_change(self, db_session, record):
        Validation.replace_all(db_session, record.id, "kramerius-links", [_result("missing")])
        db_session.commit()

        assert Validation.replace_all(db_session, record.id, "kramerius-links", []) is True
        db_session.commit()

        assert (
            db_session.query(Validation)
            .filter_by(catalog_record_id=record.id, validator="kramerius-links")
            .count()
            == 0
        )


@pytest.mark.db
@pytest.mark.redis
class TestWarmingAWindowReplacesPerRecordLookups:
    def test_get_after_warm_costs_no_query(self, db_session, marc_cache_client):
        marc_record = load_test_record("MZK01-001217709.mrc")
        ids = [
            create_catalog_record(db_session, "MZK01", f"00071{i:04d}", marc_record).id
            for i in range(8)
        ]
        db_session.commit()
        db_session.expunge_all()

        with _CountStatements(db_session, "select") as counted:
            CatalogRecord.warm(db_session, ids)
            records = [db_session.get(CatalogRecord, record_id) for record_id in ids]

        assert all(record is not None for record in records)
        assert counted.count == 1, (
            f"{counted.count} SELECTs for {len(ids)} records after warming:\n"
            + "\n".join(counted.statements)
        )

    def test_get_still_works_when_the_window_was_never_warmed(self, db_session, marc_cache_client):
        """The warm-up is an optimisation; a cycled session must still work."""
        record = create_catalog_record(
            db_session, "MZK01", "000720001", load_test_record("MZK01-001217709.mrc")
        )
        record_id = record.id
        db_session.commit()
        db_session.expunge_all()

        assert db_session.get(CatalogRecord, record_id) is not None

    def test_warming_nothing_is_not_a_query(self, db_session):
        with _CountStatements(db_session, "select") as counted:
            CatalogRecord.warm(db_session, [])
        assert counted.count == 0

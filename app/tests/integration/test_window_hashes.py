"""The windowed hash prefetch has to answer for every record it was asked about."""

import pytest


@pytest.mark.db
class TestWindowHashesCoverEveryRecord:
    def test_a_record_with_no_results_is_still_present(self, db_session):
        """The window's answer for such a record is {} — which is falsy.

        Reading it with `or` sent every one of them back to the database for an
        answer already in hand, and on a first pass that is every record.
        """
        from catalog_records.tasks import _result_hashes_for

        ids = ["MZK01-000000001", "MZK01-000000002"]
        hashes = _result_hashes_for(db_session, ids)

        for record_id in ids:
            assert record_id in hashes, "the window must answer for every record it was asked about"
            assert hashes[record_id] == {}
            assert not hashes[record_id], "an empty answer is falsy — read it by membership"


@pytest.mark.db
class TestWindowAnswerIsUsedEvenWhenEmpty:
    def test_an_empty_window_answer_is_not_recomputed(self, db_session, monkeypatch):
        """A record the window answered for must not be asked again."""
        from catalog_records import tasks

        def refuse(*_args, **_kwargs):
            raise AssertionError("went back to the database for an answer the window had")

        monkeypatch.setattr(tasks, "_compute_result_hashes", refuse)

        assert tasks._old_hashes_for(db_session, "MZK01-000000001", {"MZK01-000000001": {}}) == {}

    def test_a_record_outside_the_window_is_computed(self, db_session, monkeypatch):
        """The fallback is still there for a record the window never covered."""
        from catalog_records import tasks

        computed: list[str] = []

        def compute(_db, record_id):
            computed.append(record_id)
            return {"comparator": ("abc", [])}

        monkeypatch.setattr(tasks, "_compute_result_hashes", compute)

        result = tasks._old_hashes_for(db_session, "MZK01-000000009", {})

        assert computed == ["MZK01-000000009"]
        assert result == {"comparator": ("abc", [])}

"""The SQL call-site tracer must name application code, not SQLAlchemy.

The capture exists to answer "which line asked for these ten thousand
queries". A stack of driver internals answers nothing — and the virtualenv
lives *under* the application root, so the obvious "is this file ours" test
admits every library frame unless it is told otherwise.
"""

import json

import pytest

from adapters import sql_tracing


@pytest.fixture(autouse=True)
def _empty_counters():
    """Counters are process-global; no test may inherit another's."""
    sql_tracing._totals.sites.clear()
    sql_tracing._totals.statements = 0
    sql_tracing._totals.total_ns = 0
    yield
    sql_tracing._totals.sites.clear()


def _a_helper_that_queries() -> tuple[str, ...]:
    """Stands in for the application code a statement is issued from."""
    return sql_tracing._capture_stack()


class TestCapturedStacksNameApplicationCode:
    def test_the_calling_function_is_in_the_stack(self):
        stack = _a_helper_that_queries()

        assert stack, "no frames captured at all"
        assert any("_a_helper_that_queries" in frame for frame in stack)

    def test_library_frames_are_left_out(self):
        """The venv is inside the app tree, so this is not free."""
        stack = _a_helper_that_queries()

        for frame in stack:
            assert "site-packages" not in frame
            assert ".venv" not in frame

    def test_the_tracer_does_not_name_itself(self):
        """Its own frames are noise in every capture it takes."""
        stack = _a_helper_that_queries()

        assert not any(frame.startswith("adapters/sql_tracing.py") for frame in stack)

    def test_frames_are_relative_and_innermost_first(self):
        stack = _a_helper_that_queries()

        assert not stack[0].startswith("/"), "paths should be relative to the app root"
        assert "tests/unit/test_sql_tracing.py" in stack[0]


class TestCountersAggregatePerCallSite:
    def test_the_same_site_accumulates(self):
        stack = ("catalog_records/tasks.py:1 loop",)
        for _ in range(3):
            sql_tracing._record("SELECT 1", 1_000_000, stack)

        snapshot = sql_tracing.snapshot()

        assert snapshot["statements"] == 3
        assert len(snapshot["sites"]) == 1
        assert snapshot["sites"][0]["count"] == 3
        assert snapshot["sites"][0]["total_ms"] == pytest.approx(3.0)

    def test_the_same_sql_from_two_places_stays_apart(self):
        """One statement issued from a loop and from a batch is two findings."""
        sql_tracing._record("SELECT 1", 1_000_000, ("a.py:1 loop",))
        sql_tracing._record("SELECT 1", 1_000_000, ("b.py:2 batch",))

        assert len(sql_tracing.snapshot()["sites"]) == 2

    def test_whitespace_in_a_statement_does_not_split_it(self):
        sql_tracing._record("SELECT\n  1", 1_000_000, ("a.py:1 loop",))
        sql_tracing._record("SELECT 1", 1_000_000, ("a.py:1 loop",))

        assert len(sql_tracing.snapshot()["sites"]) == 1

    def test_sites_come_back_most_expensive_first(self):
        sql_tracing._record("SELECT cheap", 1_000_000, ("a.py:1 a",))
        sql_tracing._record("SELECT dear", 9_000_000, ("b.py:2 b",))

        assert sql_tracing.snapshot()["sites"][0]["sql"] == "SELECT dear"


class TestDumpIsReadable:
    def test_a_dump_round_trips(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sql_tracing.config.sql_trace, "output_dir", str(tmp_path))
        sql_tracing._record("SELECT 1", 2_000_000, ("catalog_records/tasks.py:1 loop",))

        path = sql_tracing.dump()

        assert path is not None
        payload = json.loads(path.read_text())
        assert payload["sites"][0]["count"] == 1
        assert payload["sites"][0]["stack"] == ["catalog_records/tasks.py:1 loop"]

    def test_no_half_written_file_is_left_behind(self, tmp_path, monkeypatch):
        """Readers poll this directory while the process keeps writing to it."""
        monkeypatch.setattr(sql_tracing.config.sql_trace, "output_dir", str(tmp_path))
        sql_tracing._record("SELECT 1", 1_000_000, ("a.py:1 a",))

        sql_tracing.dump()

        assert list(tmp_path.glob("*.part")) == []


class TestItStaysOffUnlessAskedFor:
    def test_install_does_nothing_when_disabled(self, monkeypatch):
        """The default path must not pay for a stack capture per query."""
        monkeypatch.setattr(sql_tracing.config.sql_trace, "enabled", False)
        monkeypatch.setattr(sql_tracing, "_installed", False)

        sql_tracing.install()

        assert sql_tracing._installed is False

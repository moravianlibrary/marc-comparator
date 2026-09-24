"""Whose comparator a linker ranks with, and when its verdict can stand."""

import logging
from typing import Any, cast

import pytest
from marc_comparator.comparators import RecordComparisonResult

from adapters.database import DatabaseSession
from comparison import UsedComparatorConfig
from comparison.models import ComparisonSettings
from comparison.tasks import load_gate_comparator

#: The functions under test never touch the session; the settings are faked.
NO_SESSION = cast(DatabaseSession, object())


class FakeSettings:
    def __init__(self, settings):
        self.settings = settings

    def get(self, _db, _scope, _schema):
        return self.settings


@pytest.fixture
def stored(monkeypatch):
    def store(**comparator):
        settings = ComparisonSettings.model_validate({"comparator": comparator})
        monkeypatch.setattr("comparison.tasks.Settings", FakeSettings(settings), raising=False)
        return settings

    return store


class TestGateComparator:
    def test_gate_uses_the_configured_scale(self, stored):
        # The whole point: a gate scoring on the class defaults makes a
        # linker's minimum_confidence mean something other than the score
        # an operator is shown.
        stored(excellent_threshold=3, moderate_threshold=9)

        gate, _equivalent = load_gate_comparator(NO_SESSION)

        assert gate is not None
        config = cast(UsedComparatorConfig, gate.config)
        assert config.excellent_threshold == 3
        assert config.moderate_threshold == 9

    def test_gate_never_calls_an_llm(self, stored):
        # It runs once per candidate, several times per record.
        stored(llm_enabled=True, nonstandard_llm_enabled=True)

        gate, _equivalent = load_gate_comparator(NO_SESSION)

        assert gate is not None
        config = cast(UsedComparatorConfig, gate.config)
        assert config.llm_enabled is False
        assert config.nonstandard_llm_enabled is False

    def test_its_verdict_stands_when_the_pipeline_has_no_llm_either(self, stored):
        stored(llm_enabled=False, nonstandard_llm_enabled=False)

        _gate, equivalent = load_gate_comparator(NO_SESSION)

        assert equivalent is True

    @pytest.mark.parametrize("config", [{"llm_enabled": True}, {"nonstandard_llm_enabled": True}])
    def test_its_verdict_does_not_stand_when_the_pipeline_asks_an_llm(self, stored, config):
        # The two are then measuring different things, so a result carried
        # from the gate would not be the one the pipeline would have reached.
        stored(**config)

        _gate, equivalent = load_gate_comparator(NO_SESSION)

        assert equivalent is False


class TestPrecomputedComparison:
    @pytest.mark.asyncio
    async def test_a_handed_in_result_is_stored_without_recomparing(self, monkeypatch):
        from comparison import tasks

        compared = 0

        class CountingComparator:
            async def run(self, a, b):
                nonlocal compared
                compared += 1
                return RecordComparisonResult(overall_score=0.1)

        saved: list[dict] = []

        class Link:
            base = "SKC"
            authority_record = type("R", (), {"id": "SKC-1", "get_record": lambda self, db: None})()

        class Record:
            id = "MZK01-1"
            authority_links = [Link()]

            def get_record(self, db):
                return None

        class Stored:
            def __init__(self, **kwargs):
                saved.append(kwargs)

            @staticmethod
            def find(*_args):
                return None

            def save(self, db, commit=False):
                pass

        monkeypatch.setattr(tasks, "Comparison", Stored)

        carried = RecordComparisonResult(overall_score=0.93)
        await tasks.handle_catalog_record_comparison(
            NO_SESSION,
            cast(Any, CountingComparator()),
            logging.getLogger("t"),
            "SKC",
            cast(Any, Record()),
            precomputed=carried,
        )

        assert compared == 0
        assert saved[0]["result"] == carried.model_dump()

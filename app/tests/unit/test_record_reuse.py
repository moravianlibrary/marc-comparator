"""The per-record loop hands down what it already has.

Every one of these covers a read that used to be repeated: a record parsed once
per window and then fetched again for each validator, a link walked from a lazy
relationship for each target base, and a window of hashes that was discarded
whenever it legitimately came back empty.
"""

import logging
from dataclasses import dataclass
from typing import Any, cast

import pytest
from marc_comparator.comparators import RecordComparisonResult

from comparison import tasks as comparison_tasks
from validation import tasks as validation_tasks

NO_SESSION = cast(Any, object())


class _RecordThatRefusesToBeRead:
    """A catalog record whose MARC must come from the caller, not from storage."""

    id = "MZK01-000000001"
    base = "MZK01"

    def __init__(self):
        self.reads = 0

    def get_record(self, _db):
        self.reads += 1
        raise AssertionError("MARC was read back although the caller supplied it")

    @property
    def authority_links(self):
        raise AssertionError("authority_links was walked although the caller supplied the link")


@dataclass
class _Validator:
    type: Any
    instance: Any


class TestValidationUsesTheSuppliedRecord:
    @pytest.mark.asyncio
    async def test_supplied_record_is_not_read_back(self, monkeypatch):
        parsed = object()
        seen: list[Any] = []

        class Instance:
            async def run(self, record):
                seen.append(record)
                return []

        monkeypatch.setattr(validation_tasks.Validation, "replace_all", lambda *a, **k: True)

        validator = _Validator(type=type("T", (), {"value": "kramerius"})(), instance=Instance())
        record = _RecordThatRefusesToBeRead()

        await validation_tasks.handle_catalog_record_validation(
            NO_SESSION, cast(Any, record), cast(Any, validator), record=cast(Any, parsed)
        )

        assert seen == [parsed]
        assert record.reads == 0

    @pytest.mark.asyncio
    async def test_without_a_supplied_record_it_still_reads_storage(self, monkeypatch):
        """The parameter is an optimisation for one caller, not a new requirement."""
        seen: list[Any] = []
        from_storage = object()

        class Instance:
            async def run(self, record):
                seen.append(record)
                return []

        class Record:
            id = "MZK01-000000002"

            def get_record(self, _db):
                return from_storage

        monkeypatch.setattr(validation_tasks.Validation, "replace_all", lambda *a, **k: True)

        validator = _Validator(type=type("T", (), {"value": "kramerius"})(), instance=Instance())
        await validation_tasks.handle_catalog_record_validation(
            NO_SESSION, cast(Any, Record()), cast(Any, validator)
        )

        assert seen == [from_storage]


class TestComparisonUsesTheSuppliedRecordAndLink:
    @pytest.mark.asyncio
    async def test_supplied_link_and_record_are_not_looked_up_again(self, monkeypatch):
        parsed = object()
        authority_parsed = object()
        compared: list[tuple[Any, Any]] = []

        class Comparator:
            async def run(self, main, other):
                compared.append((main, other))
                return RecordComparisonResult(overall_score=0.5)

        class Authority:
            id = "SKC-1"

            def get_record(self, _db):
                return authority_parsed

        class Link:
            base = "SKC"
            authority_record = Authority()

        saved: list[dict] = []

        class Stored:
            def __init__(self, **kwargs):
                saved.append(kwargs)

            @staticmethod
            def find(*_args):
                return None

            def save(self, _db, commit=False):
                pass

        monkeypatch.setattr(comparison_tasks, "Comparison", Stored)
        record = _RecordThatRefusesToBeRead()

        await comparison_tasks.handle_catalog_record_comparison(
            NO_SESSION,
            cast(Any, Comparator()),
            logging.getLogger("t"),
            "SKC",
            cast(Any, record),
            record=cast(Any, parsed),
            link=cast(Any, Link()),
        )

        assert compared == [(parsed, authority_parsed)]
        assert record.reads == 0
        assert saved and saved[0]["other_record_id"] == "SKC-1"

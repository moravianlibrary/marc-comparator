"""A link that still says what it said must not be written again.

A pass over already-linked records reaches scenario_found_link_update for
every one of them. It used to rewrite the link row, the authority record's
timestamp and source, its search text — three jq queries over the MARC — and
its sector, whether or not the linker had come back with anything new.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from authority_linking.tasks import (
    LinkActionResult,
    _link_update_would_write_nothing,
    scenario_found_link_update,
)

STORED = b"\x00\x01authority-as-stored"
NO_SESSION = cast(Any, object())


class _AuthorityRecord:
    id = "SKC-000000001"
    base = "SKC"
    system_number = "000000001"

    def __init__(self, source_name: str = "marcxml-dump"):
        self.source_name = source_name
        self.latest_sync = None
        self.rewrites = 0

    def update_search_text_from(self, _record):
        self.rewrites += 1


class _Link:
    def __init__(self, confidence: float = 0.95, source_name: str = "marcxml-dump"):
        self.confidence = confidence
        self.authority_record = _AuthorityRecord(source_name)
        self.saves = 0

    def save(self, _db, commit=False):  # noqa: FBT002
        self.saves += 1


def _found(marc: bytes = STORED, confidence: float = 0.95):
    return SimpleNamespace(confidence=confidence, record=SimpleNamespace(_marc=marc))


def _linker(name: str = "marcxml-dump"):
    return SimpleNamespace(linker=SimpleNamespace(value=name))


class _Buffer:
    def __init__(self, holding: bool = False):
        self.holding = holding
        self.added: list[tuple] = []

    def holds(self, _base, _system_number) -> bool:
        return self.holding

    def add(self, base, system_number, marc):
        self.added.append((base, system_number, marc))


class TestNothingIsWrittenWhenNothingMoved:
    def test_an_identical_link_writes_nothing(self):
        link = _Link()
        stored = {link.authority_record.id: STORED}

        results = scenario_found_link_update(
            NO_SESSION,
            cast(Any, _found()),
            cast(Any, _linker()),
            cast(Any, link),
            cast(Any, _Buffer()),
            stored,
        )

        assert results == [LinkActionResult.UnchangedLink]
        assert link.saves == 0
        assert link.authority_record.rewrites == 0, "recomputed search text for no reason"
        assert link.authority_record.latest_sync is None


class TestEveryRealChangeStillLands:
    @pytest.mark.parametrize(
        ("found", "linker", "stored_marc", "why"),
        [
            (_found(marc=b"new bytes"), _linker(), STORED, "the authority MARC changed"),
            (_found(confidence=0.5), _linker(), STORED, "the confidence changed"),
            (_found(), _linker("knihovny-cz"), STORED, "a different linker answered"),
            (_found(), _linker(), None, "nothing was prefetched to compare against"),
        ],
    )
    def test_the_update_is_written(self, found, linker, stored_marc, why):
        link = _Link()
        stored = None if stored_marc is None else {link.authority_record.id: stored_marc}

        results = scenario_found_link_update(
            NO_SESSION,
            cast(Any, found),
            cast(Any, linker),
            cast(Any, link),
            cast(Any, _Buffer()),
            stored,
        )

        assert results == [
            LinkActionResult.UpdatedLink,
            LinkActionResult.UpdatedAuthorityRecord,
        ], why
        assert link.saves == 1, why
        assert link.authority_record.rewrites == 1, why

    def test_a_record_missing_from_the_prefetch_is_written(self):
        """Absent is not the same as unchanged."""
        link = _Link()

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            cast(Any, _linker()),
            cast(Any, link),
            cast(Any, _Buffer()),
            {},
        )

    def test_a_buffered_record_is_written(self):
        """Buffered MARC still reads as its previous self, so stored bytes lie."""
        link = _Link()

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            cast(Any, _linker()),
            cast(Any, link),
            cast(Any, _Buffer(holding=True)),
            {link.authority_record.id: STORED},
        )

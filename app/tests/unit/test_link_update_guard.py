"""A link that still says what it said must not be written again.

A pass over already-linked records reaches scenario_found_link_update for
every one of them. It used to rewrite the link row, the authority record's
timestamp and source, its search text — three jq queries over the MARC — and
its sector, whether or not the linker had come back with anything new.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from marc_comparator.authority_linkers import MatchRoute

from authority_linking.tasks import (
    LinkActionResult,
    _link_update_would_write_nothing,
    scenario_found_link_update,
)

STORED = b"\x00\x01authority-as-stored"
AGENCY = "ABA001"
#: What the linker reports having weighed, matching `_Link`'s own column.
CANDIDATES = 1
NO_SESSION = cast(Any, object())


class _AuthorityRecord:
    id = "SKC-000000001"
    base = "SKC"
    system_number = "000000001"

    def __init__(self, source_name: str = "marcxml-dump", agency: str | None = AGENCY):
        self.source_name = source_name
        self.cataloguing_agency = agency
        self.latest_sync = None
        self.rewrites = 0

    def update_search_text_from(self, _record):
        self.rewrites += 1


class _Link:
    def __init__(
        self,
        confidence: float = 0.95,
        source_name: str = "marcxml-dump",
        agency: str | None = AGENCY,
        matched_by: str | None = MatchRoute.Identifier.value,
        matched_identifier: str | None = "cnb",
        authority_base: str = "SKC",
        authority_sysno: str = "000000001",
        candidate_count: int | None = 1,
    ):
        self.main_record_id = "MZK01-000000042"
        self.base = "SKC"
        self.outcome = "Linked"
        self.candidate_count = candidate_count
        self.confidence = confidence
        self.matched_by = matched_by
        self.matched_identifier = matched_identifier
        self.authority_base = authority_base
        self.authority_sysno = authority_sysno
        self.authority_record = _AuthorityRecord(source_name, agency)
        self.saves = 0

    @property
    def linked_record(self):
        """What the entity exposes for a row that is an accepted link."""
        return self.authority_record

    def save(self, _db, commit=False):  # noqa: FBT002
        self.saves += 1


class _VariableFields:
    """Just enough of the MARC accessor for the agency reader."""

    def __init__(self, agency: str | None):
        self._agency = agency

    def query_subfield_values(self, _jq):
        return [self._agency] if self._agency else []


def _found(
    marc: bytes = STORED,
    confidence: float = 0.95,
    matched_by: MatchRoute | None = MatchRoute.Identifier,
    base: str = "SKC",
    system_number: str = "000000001",
    agency: str | None = AGENCY,
    matched_identifier: str | None = "cnb",
):
    return SimpleNamespace(
        base=base,
        system_number=system_number,
        confidence=confidence,
        matched_by=matched_by,
        matched_identifier=matched_identifier,
        record=SimpleNamespace(_marc=marc, variable_fields=_VariableFields(agency)),
    )


def _linker(name: str | None = "marcxml-dump") -> str | None:
    """The linker as the write path now takes it: a name, or nothing.

    A candidate need not come from a linker — a cataloguer's claim can put one
    in front of the pipeline that retrieval never returned — so what reaches
    here is the name to record, which may be None.
    """

    return name


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
            _linker(),
            cast(Any, link),
            cast(Any, _Buffer()),
            stored,
            CANDIDATES,
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
            (
                _found(matched_by=MatchRoute.Title),
                _linker(),
                STORED,
                "the same record was found a different way",
            ),
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
            CANDIDATES,
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
            _linker(),
            cast(Any, link),
            cast(Any, _Buffer()),
            {},
            CANDIDATES,
        )

    def test_a_buffered_record_is_written(self):
        """Buffered MARC still reads as its previous self, so stored bytes lie."""
        link = _Link()

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            cast(Any, _Buffer(holding=True)),
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

    def test_a_link_predating_the_natural_key_is_written(self):
        """A link from before the candidate's own key was stored fills it in.

        Nothing else moved — same record, same confidence, same route — so
        without this the two columns would stay empty for as long as the link
        went on being re-found, and the candidate would have no key of its own.
        """

        link = _Link(authority_base=None, authority_sysno=None)  # pyright: ignore[reportArgumentType]

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            cast(Any, _Buffer()),
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

    def test_a_link_predating_the_route_is_written(self):
        """A link from before the route was recorded has to pick one up.

        Its confidence is the same one it has always had, so the route is the
        only thing that moved; without it the column would keep its null for as
        long as the link went on agreeing with the linker.
        """

        link = _Link(matched_by=None)

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            cast(Any, _Buffer()),
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

    def test_a_changed_candidate_count_is_written(self):
        """How many were weighed is stored, and derivable from nothing else.

        An unambiguous winner is kept without its runner-ups, so this column
        is the only thing separating "there was one candidate" from "there
        were eight and seven were not worth keeping".
        """

        link = _Link(candidate_count=1)

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            cast(Any, _Buffer()),
            {link.authority_record.id: STORED},
            8,
        )

    def test_a_linker_that_reports_no_route_leaves_the_column_alone(self):
        """Nothing to record is not a change worth a write."""

        link = _Link(matched_by=None)

        assert _link_update_would_write_nothing(
            cast(Any, _found(matched_by=None)),
            _linker(),
            cast(Any, link),
            cast(Any, _Buffer()),
            {link.authority_record.id: STORED},
            CANDIDATES,
        )


class TestAColumnAddedLaterStillFills:
    def test_a_link_predating_the_agency_is_written(self):
        """47,777 links already exist and nothing else would ever rewrite them.

        The authority record's cataloguing agency is read off the same MARC
        that is already stored byte for byte, so every other check here passes
        and the column would stay null forever — taking the facet built on it
        with it.
        """

        link = _Link(agency=None)

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            None,
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

    def test_an_agency_already_stored_is_not_a_change(self):
        link = _Link()

        assert _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            None,
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

    def test_a_link_predating_the_identifier_is_written(self):
        """The same trap as the agency column, one release later.

        Nothing else about an existing link changes when the column is added,
        so every other check passes and `matched_identifier` would stay null
        over every link already stored — and the facet built on it would stay
        empty for good.
        """

        link = _Link(matched_identifier=None)

        assert not _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            None,
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

    def test_an_identifier_already_stored_is_not_a_change(self):
        link = _Link()

        assert _link_update_would_write_nothing(
            cast(Any, _found()),
            _linker(),
            cast(Any, link),
            None,
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

    def test_a_pair_now_found_by_a_different_identifier_is_written(self):
        # The dump changed and the pair is no longer retrieved by its ČNB.
        # That is worth recording: it is what the score has to be read against.
        link = _Link(matched_identifier="cnb")

        assert not _link_update_would_write_nothing(
            cast(Any, _found(matched_identifier="isbn")),
            _linker(),
            cast(Any, link),
            None,
            {link.authority_record.id: STORED},
            CANDIDATES,
        )

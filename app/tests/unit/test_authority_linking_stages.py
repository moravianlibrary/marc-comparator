"""Linking stops at the first confident linker and falls back to the best score."""

import logging
from typing import Any, cast

import pytest
from marc_comparator.authority_linkers import (
    AuthorityLink,
    AuthorityLinker,
    BaseAuthorityLinker,
    LinkProposal,
)
from marcdantic import MarcRecord

from authority_linking.tasks import AuthorityLinkerInstance, find_best_link_for_record
from entities.catalog_record import CatalogRecord

LEADER = "00000nam a2200000 a 4500"
LOGGER = logging.getLogger(__name__)


def marc_record() -> MarcRecord:
    return MarcRecord.model_validate(
        {
            "leader": LEADER,
            "fixed_fields": {
                "001": "000000001",
                "005": "20200101000000.0",
                "008": "200101s2020    xr            000 0 cze d",
            },
            "variable_fields": {},
        }
    )


def catalog_record() -> CatalogRecord:
    record = CatalogRecord(base="MZK01", system_number="000000001")
    record.id = "MZK01/000000001"
    return record


class CountingLinker:
    """Report a fixed confidence and record whether it was consulted."""

    def __init__(self, system_number: str, confidence: float | None) -> None:
        self.system_number = system_number
        self.confidence = confidence
        self.calls = 0

    async def run(self, base, system_number, record, target_base) -> LinkProposal:
        self.calls += 1
        link = AuthorityLink(
            base=target_base,
            system_number=self.system_number,
            record=marc_record(),
            confidence=self.confidence,
        )
        return LinkProposal(link=link, candidates=[link], candidate_count=1)


class SilentLinker:
    def __init__(self) -> None:
        self.calls = 0

    async def run(self, base, system_number, record, target_base) -> LinkProposal:
        self.calls += 1
        return LinkProposal.nothing_found()


def instance(linker: AuthorityLinker, stub: object) -> AuthorityLinkerInstance:
    return AuthorityLinkerInstance(linker, cast(BaseAuthorityLinker[Any], stub))


async def link_with(*stubs: object, confident_threshold: float = 0.9):
    linkers = [
        instance(AuthorityLinker.KnihovnyCz if index == 0 else AuthorityLinker.MarcXmlDump, stub)
        for index, stub in enumerate(stubs)
    ]
    return await find_best_link_for_record(
        catalog_record(), linkers, "SKC", marc_record(), LOGGER, confident_threshold
    )


@pytest.mark.asyncio
async def test_a_confident_first_linker_stops_the_rest():
    first = CountingLinker("000000111", 0.95)
    second = CountingLinker("000000222", 0.99)

    decision = await link_with(first, second)

    link = decision.accepted.link if decision.accepted else None

    linker = decision.accepted.linker if decision.accepted else None

    assert link is not None
    assert link.system_number == "000000111"
    assert linker == AuthorityLinker.KnihovnyCz.value
    # Even a higher-scoring rival is never consulted: the answer was already
    # good enough, and asking costs a lookup per record.
    assert second.calls == 0


@pytest.mark.asyncio
async def test_a_later_linker_can_be_the_confident_one():
    first = SilentLinker()
    second = CountingLinker("000000222", 0.93)

    decision = await link_with(first, second)

    link = decision.accepted.link if decision.accepted else None

    assert link is not None
    assert link.system_number == "000000222"
    assert first.calls == 1


@pytest.mark.asyncio
async def test_without_confidence_every_linker_is_consulted_and_the_best_wins():
    first = CountingLinker("000000111", 0.74)
    second = CountingLinker("000000222", 0.86)

    decision = await link_with(first, second)

    link = decision.accepted.link if decision.accepted else None

    linker = decision.accepted.linker if decision.accepted else None

    assert link is not None
    assert link.system_number == "000000222"
    assert link.confidence == 0.86
    assert linker == AuthorityLinker.MarcXmlDump.value
    assert first.calls == 1
    assert second.calls == 1


@pytest.mark.asyncio
async def test_order_decides_between_equally_confident_linkers():
    first = CountingLinker("000000111", 0.95)
    second = CountingLinker("000000222", 0.95)

    decision = await link_with(first, second)

    link = decision.accepted.link if decision.accepted else None

    assert link is not None
    assert link.system_number == "000000111"


@pytest.mark.asyncio
async def test_a_linker_reporting_no_confidence_ranks_last():
    # A missing confidence is not evidence of a good match, so it must not beat
    # a linker that measured one.
    first = CountingLinker("000000111", None)
    second = CountingLinker("000000222", 0.71)

    decision = await link_with(first, second)

    link = decision.accepted.link if decision.accepted else None

    assert link is not None
    assert link.system_number == "000000222"


@pytest.mark.asyncio
async def test_the_threshold_is_configurable():
    first = CountingLinker("000000111", 0.8)
    second = CountingLinker("000000222", 0.99)

    decision = await link_with(first, second, confident_threshold=0.75)

    link = decision.accepted.link if decision.accepted else None

    assert link is not None
    assert link.system_number == "000000111"
    assert second.calls == 0

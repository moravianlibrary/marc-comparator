"""A linker that fails must not be reported as a linker that found nothing."""

import logging
from typing import cast

import pytest
from marc_comparator.authority_linkers import AuthorityLink, AuthorityLinker, BaseAuthorityLinker
from marcdantic import MarcRecord

from authority_linking.tasks import (
    AuthorityLinkerInstance,
    AuthorityLinkingFailed,
    find_best_link_for_record,
)
from entities.catalog_record import CatalogRecord

LEADER = "00000nam a2200000 a 4500"


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


def instance(linker: AuthorityLinker, run) -> AuthorityLinkerInstance:
    stub = type("StubLinker", (), {"run": run})()
    return AuthorityLinkerInstance(linker, cast(BaseAuthorityLinker, stub))


async def raises(*args, **kwargs):
    raise RuntimeError("lookup service is down")


async def finds_nothing(*args, **kwargs):
    return None


async def finds_link(*args, **kwargs):
    return AuthorityLink(
        base="SKC", system_number="000123456", record=marc_record(), confidence=1.0
    )


@pytest.mark.asyncio
async def test_failure_is_raised_rather_than_reported_as_no_link():
    # The caller deletes an existing link whenever nothing is found, so a lookup
    # that never completed has to be distinguishable from an empty result.
    with pytest.raises(AuthorityLinkingFailed):
        await find_best_link_for_record(
            catalog_record(),
            [instance(AuthorityLinker.MarcXmlDump, raises)],
            "SKC",
            marc_record(),
            logging.getLogger(__name__),
        )


@pytest.mark.asyncio
async def test_partial_failure_still_refuses_to_confirm_an_empty_result():
    with pytest.raises(AuthorityLinkingFailed):
        await find_best_link_for_record(
            catalog_record(),
            [
                instance(AuthorityLinker.KnihovnyCz, finds_nothing),
                instance(AuthorityLinker.MarcXmlDump, raises),
            ],
            "SKC",
            marc_record(),
            logging.getLogger(__name__),
        )


@pytest.mark.asyncio
async def test_a_found_link_survives_another_linker_failing():
    link, linker = await find_best_link_for_record(
        catalog_record(),
        [
            instance(AuthorityLinker.KnihovnyCz, raises),
            instance(AuthorityLinker.MarcXmlDump, finds_link),
        ],
        "SKC",
        marc_record(),
        logging.getLogger(__name__),
    )

    assert link is not None
    assert linker is not None
    assert linker.linker == AuthorityLinker.MarcXmlDump


@pytest.mark.asyncio
async def test_every_linker_reporting_nothing_is_a_real_empty_result():
    assert await find_best_link_for_record(
        catalog_record(),
        [instance(AuthorityLinker.MarcXmlDump, finds_nothing)],
        "SKC",
        marc_record(),
        logging.getLogger(__name__),
    ) == (None, None)

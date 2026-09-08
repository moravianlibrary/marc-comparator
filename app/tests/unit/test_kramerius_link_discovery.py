"""Unit tests for KrameriusLinksValidator.find_kramerius_links (identifier matching).

Stubs the Solr client so no network is involved. The numbers here come from the
July 2026 incident, where a ČNB number shared by dozens of unrelated documents turned
into dozens of bogus 856 links per record.
"""

import pytest
from kramerius import Model
from kramerius.schemas import KrameriusDocument
from marc_comparator.validators.kramerius_links import (
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from marcdantic import MarcRecord

LEADER = "00000nam a2200000 a 4500"

# MZK01-001450171, "LibreOffice Writer: praktický průvodce"
OWN_PID = "uuid:27055693-9413-43d3-8e61-d5048b14dd16"
ISBN = "978-80-904248-9-0"
NBN = "cnb002657972"


def make_record(*, isbn: str | None = ISBN, nbn: str | None = NBN) -> MarcRecord:
    variable_fields = {}
    if isbn:
        variable_fields["020"] = [{"ind1": " ", "ind2": " ", "subfields": {"a": [isbn]}}]
    if nbn:
        variable_fields["015"] = [{"ind1": " ", "ind2": " ", "subfields": {"a": [nbn]}}]

    return MarcRecord.model_validate(
        {
            "leader": LEADER,
            "fixed_fields": {
                "001": "001450171",
                "005": "20200101000000.0",
                "008": "200101s2020    xr            000 0 cze d",
            },
            "variable_fields": variable_fields,
        }
    )


def doc(pid: str, *, isbn=None, nbn=None, model_path="monograph", own_pid_path=None):
    return KrameriusDocument.model_validate(
        {
            "own_pid_path": own_pid_path or pid,
            "own_model_path": model_path,
            "level": 0,
            "id_isbn": isbn,
            "id_ccnb": nbn,
        }
    )


class StubSearch:
    """Returns a fixed doc list for the identifier query, nothing for pid lookups."""

    def __init__(self, docs):
        self._docs = docs

    def search(self, query, fl=None):
        return list(self._docs)


def make_validator(docs, **config):
    validator = KrameriusLinksValidator(KrameriusLinksValidatorConfig(**config))
    validator.client.Search = StubSearch(docs)  # type: ignore[assignment]
    return validator


@pytest.mark.asyncio
async def test_polluted_nbn_is_dropped_but_exact_isbn_hit_survives():
    """The real incident: one ČNB matched 41 unrelated documents.

    Only the document that also matches the ISBN should survive.
    """
    docs = [doc(OWN_PID, isbn=[ISBN], nbn=[NBN])]
    docs += [doc(f"uuid:unrelated-{i}", nbn=[NBN]) for i in range(40)]

    links = await make_validator(docs).find_kramerius_links(make_record(), [])

    assert [link.pid for link in links] == [OWN_PID]


@pytest.mark.asyncio
async def test_identifier_under_the_cap_is_kept():
    """A record legitimately split into a few documents keeps all of them."""
    docs = [doc(f"uuid:volume-{i}", nbn=[NBN]) for i in range(3)]

    links = await make_validator(docs).find_kramerius_links(make_record(), [])

    assert sorted(link.pid for link in links) == [
        "uuid:volume-0",
        "uuid:volume-1",
        "uuid:volume-2",
    ]


@pytest.mark.asyncio
async def test_cap_is_configurable():
    docs = [doc(f"uuid:volume-{i}", nbn=[NBN]) for i in range(3)]

    links = await make_validator(docs, max_roots_per_identifier=2).find_kramerius_links(
        make_record(), []
    )

    assert links == []


@pytest.mark.asyncio
async def test_pollution_in_one_identifier_does_not_discard_another():
    """Dropping ČNB must not take the ISBN's own hits with it."""
    isbn_hit = doc("uuid:from-isbn", isbn=[ISBN])
    docs = [isbn_hit] + [doc(f"uuid:unrelated-{i}", nbn=[NBN]) for i in range(40)]

    links = await make_validator(docs).find_kramerius_links(make_record(), [])

    assert [link.pid for link in links] == ["uuid:from-isbn"]


@pytest.mark.asyncio
async def test_root_model_comes_from_the_root_not_the_leaf():
    """A hit on a child names the parent's model, so the parent stays linkable.

    own_pid_path and own_model_path both run root -> leaf; pairing the root pid with
    the leaf's model wrongly marked every such parent non-linkable.
    """
    root = "uuid:parent-monograph"
    docs = [
        doc(
            "uuid:child-unit",
            isbn=[ISBN],
            own_pid_path=f"{root}/uuid:child-unit",
            model_path="monograph/monographunit",
        )
    ]

    links = await make_validator(docs).find_kramerius_links(make_record(), [])

    assert len(links) == 1
    assert links[0].pid == root
    assert links[0].model == Model.Monograph
    assert links[0].has_wrong_model is False


@pytest.mark.asyncio
async def test_unattributable_hits_are_capped_too():
    """Hits matching no searched value verbatim get the same plausibility check."""
    docs = [doc(f"uuid:mystery-{i}") for i in range(40)]

    links = await make_validator(docs).find_kramerius_links(make_record(), [])

    assert links == []

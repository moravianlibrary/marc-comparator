"""Unit tests for Kramerius identifier matching (no network — the Solr client is stubbed).

The numbers come from the July 2026 incident, where ČNB numbers shared by unrelated
Kramerius documents turned into dozens of bogus 856 links per record.
"""

import pytest
from kramerius import Model
from kramerius.schemas import KrameriusDocument
from marc_comparator.validators import ValidityStatus
from marc_comparator.validators.kramerius_links import (
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from marcdantic import MarcRecord

LEADER = "00000nam a2200000 a 4500"
REVIEW_REASON = "identifier_matches_multiple_documents"

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
            "pid": pid,
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


def polluted_nbn_docs(extra: int = 40):
    """The real shape: the record's own document plus N unrelated ones sharing its ČNB."""
    return [doc(OWN_PID, isbn=[ISBN], nbn=[NBN])] + [
        doc(f"uuid:unrelated-{i}", nbn=[NBN]) for i in range(extra)
    ]


@pytest.mark.asyncio
async def test_single_match_is_linked():
    links, ambiguous = await make_validator(
        [doc(OWN_PID, isbn=[ISBN], nbn=[NBN])]
    ).find_kramerius_links(make_record(), [])

    assert [link.pid for link in links] == [OWN_PID]
    assert ambiguous == []


@pytest.mark.asyncio
async def test_identifier_matching_several_documents_is_withheld_for_review():
    links, ambiguous = await make_validator(
        [doc(f"uuid:volume-{i}", nbn=[NBN]) for i in range(3)]
    ).find_kramerius_links(make_record(), [])

    assert links == []
    assert len(ambiguous) == 1
    assert ambiguous[0].values == [NBN]
    assert ambiguous[0].pids == ["uuid:volume-0", "uuid:volume-1", "uuid:volume-2"]


@pytest.mark.asyncio
async def test_threshold_is_configurable():
    docs = [doc(f"uuid:volume-{i}", nbn=[NBN]) for i in range(3)]

    links, ambiguous = await make_validator(
        docs, max_documents_per_identifier=3
    ).find_kramerius_links(make_record(), [])

    assert sorted(link.pid for link in links) == [
        "uuid:volume-0",
        "uuid:volume-1",
        "uuid:volume-2",
    ]
    assert ambiguous == []


@pytest.mark.asyncio
async def test_one_bad_identifier_does_not_withhold_another_identifiers_hit():
    """The record's own document is found via ISBN, so the polluted ČNB cannot bury it."""
    links, ambiguous = await make_validator(polluted_nbn_docs()).find_kramerius_links(
        make_record(), []
    )

    assert [link.pid for link in links] == [OWN_PID]
    assert [a.field.value for a in ambiguous if a.field] == ["id_ccnb"]


@pytest.mark.asyncio
async def test_unattributable_hits_are_reviewed_too():
    """Hits matching no searched value verbatim get the same plausibility check."""
    links, ambiguous = await make_validator(
        [doc(f"uuid:mystery-{i}") for i in range(40)]
    ).find_kramerius_links(make_record(), [])

    assert links == []
    assert len(ambiguous) == 1
    assert ambiguous[0].field is None


@pytest.mark.asyncio
async def test_root_model_comes_from_the_root_not_the_leaf():
    """A hit on a child names the parent's model, so the parent stays linkable.

    own_pid_path and own_model_path both run root -> leaf; pairing the root pid with
    the leaf's model wrongly marked every such parent non-linkable.
    """
    root = "uuid:parent-monograph"
    links, _ = await make_validator(
        [
            doc(
                "uuid:child-unit",
                isbn=[ISBN],
                own_pid_path=f"{root}/uuid:child-unit",
                model_path="monograph/monographunit",
            )
        ]
    ).find_kramerius_links(make_record(), [])

    assert len(links) == 1
    assert links[0].pid == root
    assert links[0].model == Model.Monograph
    assert links[0].has_wrong_model is False


# ── the review result as the curator sees it ──────────────────────────────────


@pytest.mark.asyncio
async def test_run_reports_the_bad_identifier_for_review():
    results = await make_validator(polluted_nbn_docs()).run(make_record())

    review = [r for r in results if r.reason == REVIEW_REASON]
    assert len(review) == 1
    assert review[0].status is ValidityStatus.ForReview

    params = review[0].params or {}
    assert params["identifier"] == "id_ccnb"
    assert params["values"] == NBN
    # 40 unrelated documents plus the record's own, which carries the ČNB too.
    assert params["count"] == "41"
    # A sample only — the identifier is reported so the full set stays one query away.
    assert len(params["pids"].split(", ")) == 10


@pytest.mark.asyncio
async def test_run_proposes_only_the_identifier_backed_link():
    """41 candidates, but only the ISBN-backed one becomes a proposed 856."""
    results = await make_validator(polluted_nbn_docs()).run(make_record())

    additions = [r for r in results if r.reason == "missing_link_in_marc"]
    assert [(r.params or {})["pid"] for r in additions] == [OWN_PID]


# ── $z part designation, taken from the linked document's title ───────────────
#
# part.number.str would be the obvious source but is empty on every top-level
# document (0 of 314 169 in MZK's index), so the title is all there is.

PART_TITLES = [
    ("O ztraceném ševci: pohorský obraz. [Díl] 1", "Díl 1"),
    ("Jalna. [Díl] 15. Co vítr přivál", "Díl 15"),
    ("Dynastie Morlandů. 9. díl. Neklidné moře", "Díl 9"),
    ("Rok na vsi: kronika moravské dědiny. Sv. 3", "Sv. 3"),
    # No part designation — must not invent one.
    ("LibreOffice Writer: praktický průvodce", None),
    ("Pěšky po jižních Čechách. 21. Z renesančních Slavonic", None),
    ("Text v pohybu četby", None),
    ("", None),
    (None, None),
]


@pytest.mark.parametrize(("title", "expected"), PART_TITLES)
def test_part_number_extraction(title, expected):
    assert make_validator([])._part_number(title) == expected


@pytest.mark.asyncio
async def test_link_carries_part_number_from_its_own_title():
    docs = [doc(OWN_PID, isbn=[ISBN])]
    docs[0].title = "Dynastie Morlandů. 9. díl. Neklidné moře"

    links, _ = await make_validator(docs).find_kramerius_links(make_record(), [])

    assert links[0].part_number == "Díl 9"


@pytest.mark.asyncio
async def test_child_hit_does_not_borrow_its_part_number_for_the_parent():
    """A child's title names the child's part, not the root's — do not copy it up."""
    root = "uuid:parent-monograph"
    docs = [
        doc(
            "uuid:child-unit",
            isbn=[ISBN],
            own_pid_path=f"{root}/uuid:child-unit",
            model_path="monograph/monographunit",
        )
    ]
    docs[0].title = "Rok na vsi. 3. Březen-Duben"

    links, _ = await make_validator(docs).find_kramerius_links(make_record(), [])

    assert links[0].pid == root
    assert links[0].part_number is None

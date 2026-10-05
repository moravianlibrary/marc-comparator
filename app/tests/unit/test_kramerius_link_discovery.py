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


def doc(
    pid: str,
    *,
    isbn=None,
    nbn=None,
    model_path: str | None = "monograph",
    own_pid_path: str | None = None,
    level: int | None = 0,
):
    return KrameriusDocument.model_validate(
        {
            "pid": pid,
            "own_pid_path": own_pid_path if own_pid_path is not None else pid,
            "own_model_path": model_path,
            "level": level,
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


class TestADocumentSolrHoldsIncompletely:
    """Solr declares level, own_model_path and own_pid_path all optional.

    They were read as given. A document missing its level is not equal to 0,
    so it was filed as "below the top" carrying `level=None` — and the reader
    that decides whether to report it asks `link.level > 0`, which raises on
    None rather than comparing. A document missing a path crashed on `.split`
    one line earlier. The harvested path has always read a missing level as 0;
    this now agrees with it.
    """

    @pytest.mark.asyncio
    async def test_a_missing_level_is_read_as_the_top_not_as_nothing(self):
        pid = "uuid:no-level"
        links, _ = await make_validator([doc(pid, level=None)]).find_kramerius_links(
            make_record(isbn=None, nbn=None), [pid]
        )

        assert [(link.pid, link.level) for link in links] == [(pid, 0)]

    @pytest.mark.asyncio
    async def test_a_level_solr_did_give_is_still_honoured(self):
        pid = "uuid:page-7"
        root = "uuid:parent-monograph"
        links, _ = await make_validator(
            [
                doc(
                    pid,
                    level=2,
                    own_pid_path=f"{root}/{pid}",
                    model_path="monograph/page",
                )
            ]
        ).find_kramerius_links(make_record(isbn=None, nbn=None), [pid])

        assert [(link.pid, link.level, link.top_level_pid) for link in links] == [(pid, 2, root)]

    @pytest.mark.asyncio
    async def test_a_document_with_no_hierarchy_is_skipped_rather_than_raising(self):
        pid = "uuid:no-paths"
        links, _ = await make_validator(
            [doc(pid, model_path=None, own_pid_path=None)]
        ).find_kramerius_links(make_record(isbn=None, nbn=None), [pid])

        assert links == []


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

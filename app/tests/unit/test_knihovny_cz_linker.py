"""The comparator gate the knihovny.cz dedup groups are judged by."""

from typing import cast

import httpx
import pytest
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]  # lxml ships no stubs
from marc_comparator.authority_linkers.knihovny_cz_linker import (
    KnihovnyCZLinker,
    KnihovnyCZLinkerConfig,
)
from marc_comparator.comparators import RecordComparisonResult
from marcdantic import MarcRecord

MARC_XML = """
<record xmlns="http://www.loc.gov/MARC21/slim">
  <leader>     nam a22      a 4500</leader>
  <controlfield tag="001">{control_number}</controlfield>
  <controlfield tag="005">20170113091406.0</controlfield>
  <controlfield tag="008">120529s2012    xr a   f f    000 0 cze d</controlfield>
  <datafield tag="245" ind1="0" ind2="0">
    <subfield code="a">Elektromagnetick&#233; z&#225;&#345;en&#237; :</subfield>
  </datafield>
</record>
"""


def marc_record(control_number: str = "mzk00001") -> MarcRecord:
    xml = MARC_XML.format(control_number=control_number).strip().encode()
    return MarcRecord.from_xml(etree.fromstring(xml))


class ScriptedComparator:
    """Return a prepared score per candidate, in the order they are compared."""

    def __init__(self, scores: list[float]) -> None:
        self.scores = list(scores)
        self.compared = 0

    async def run(self, record_a: MarcRecord, record_b: MarcRecord) -> RecordComparisonResult:
        score = self.scores[self.compared]
        self.compared += 1
        return RecordComparisonResult(overall_score=score)


def linker_with_dedup(
    monkeypatch: pytest.MonkeyPatch,
    dedup_ids: list[str],
    scores: list[float],
    **config: object,
) -> tuple[KnihovnyCZLinker, ScriptedComparator, list[str]]:
    """A linker whose API answers are scripted and whose scores are prepared."""

    linker = KnihovnyCZLinker(KnihovnyCZLinkerConfig(**config))  # pyright: ignore[reportArgumentType]
    comparator = ScriptedComparator(scores)
    linker._comparator = cast(object, comparator)  # pyright: ignore[reportAttributeAccessIssue]

    fetched: list[str] = []

    async def fake_dedup_ids(id: str) -> list[str]:
        return dedup_ids

    async def fake_record(id: str) -> MarcRecord:
        fetched.append(id)
        return marc_record(f"skc{len(fetched)}")

    monkeypatch.setattr(linker, "_get_dedup_ids", fake_dedup_ids)
    monkeypatch.setattr(linker, "_get_record", fake_record)
    return linker, comparator, fetched


async def run_linker(linker: KnihovnyCZLinker):
    return await linker.run("MZK01", "000123456", marc_record(), "SKC")


class TestConfidenceGate:
    async def test_reports_the_measured_score_not_certainty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        linker, _, _ = linker_with_dedup(monkeypatch, ["caslin.SKC01-001217729"], [0.83])

        link = await run_linker(linker)

        assert link is not None
        assert link.system_number == "001217729"
        assert link.confidence == pytest.approx(0.83)

    async def test_dedup_group_below_the_floor_is_no_link(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Somebody else's deduplication grouped two records this catalogue does
        # not consider the same thing. Reporting it would launder their mistake.
        linker, _, _ = linker_with_dedup(monkeypatch, ["caslin.SKC01-001217729"], [0.55])

        assert await run_linker(linker) is None

    async def test_the_floor_is_inclusive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        linker, _, _ = linker_with_dedup(
            monkeypatch, ["caslin.SKC01-001217729"], [0.7], minimum_confidence=0.7
        )

        link = await run_linker(linker)

        assert link is not None

    async def test_floor_is_configurable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        linker, _, _ = linker_with_dedup(
            monkeypatch, ["caslin.SKC01-001217729"], [0.55], minimum_confidence=0.5
        )

        link = await run_linker(linker)

        assert link is not None
        assert link.confidence == pytest.approx(0.55)


class TestCandidateSelection:
    async def test_best_of_several_dedup_records_wins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A dedup group naming several records in the target base used to leave
        # whichever came last; now the scores decide.
        linker, comparator, fetched = linker_with_dedup(
            monkeypatch,
            ["caslin.SKC01-000000111", "caslin.SKC01-000000222", "caslin.SKC01-000000333"],
            [0.75, 0.95, 0.80],
        )

        link = await run_linker(linker)

        assert link is not None
        assert link.system_number == "000000222"
        assert link.confidence == pytest.approx(0.95)
        assert comparator.compared == 3
        assert len(fetched) == 3

    async def test_duplicate_dedup_ids_are_fetched_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        linker, comparator, fetched = linker_with_dedup(
            monkeypatch,
            ["caslin.SKC01-000000111", "caslin.SKC01-000000111"],
            [0.95],
        )

        link = await run_linker(linker)

        assert link is not None
        assert comparator.compared == 1
        assert fetched == ["caslin.SKC01-000000111"]

    async def test_no_target_record_costs_no_comparison(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        linker, comparator, fetched = linker_with_dedup(monkeypatch, ["mzk.MZK03-000000111"], [])

        assert await run_linker(linker) is None
        assert comparator.compared == 0
        assert fetched == []

    async def test_unsupported_base_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        linker, _, _ = linker_with_dedup(monkeypatch, [], [])

        with pytest.raises(ValueError, match="Unsupported base"):
            await linker.run("NKC01", "000123456", marc_record(), "SKC")


class TestConfigDefaults:
    def test_default_floor_matches_the_moderate_band(self) -> None:
        assert KnihovnyCZLinkerConfig().minimum_confidence == pytest.approx(0.7)

    def test_client_is_built_without_touching_the_network(self) -> None:
        linker = KnihovnyCZLinker(KnihovnyCZLinkerConfig())

        assert isinstance(linker.client, httpx.AsyncClient)


class TestUnknownRecords:
    """knihovny.cz has no 404, so its 400 has to be read before it is trusted."""

    @staticmethod
    def response(status_code: int, payload: dict) -> httpx.Response:
        return httpx.Response(
            status_code,
            json=payload,
            request=httpx.Request("GET", "https://www.knihovny.cz/api/v1/record"),
        )

    def linker(self, monkeypatch: pytest.MonkeyPatch, response: httpx.Response):
        linker = KnihovnyCZLinker(KnihovnyCZLinkerConfig())

        async def fake_get(*args: object, **kwargs: object) -> httpx.Response:
            return response

        monkeypatch.setattr(linker.client, "get", fake_get)
        return linker

    async def test_record_we_do_not_share_has_no_dedup_group(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Every id knihovny.cz cannot load answers this way, including our own
        # well-formed ones it has never indexed. Raising for it abandoned the
        # record entirely — no comparison, no validation, not marked processed.
        linker = self.linker(
            monkeypatch,
            self.response(400, {"status": "ERROR", "statusMessage": "Error loading record"}),
        )

        assert await linker._get_dedup_ids("mzk.MZK03-001081160") == []

    async def test_unloadable_target_is_skipped_not_fetched_as_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        linker = self.linker(
            monkeypatch,
            self.response(400, {"status": "ERROR", "statusMessage": "Error loading record"}),
        )

        assert await linker._get_record("caslin.SKC01-000000000") is None

    async def test_other_bad_requests_still_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # "No link" is taken as evidence that an existing link is obsolete and
        # deletes it, so only the answer that really means "not here" may be
        # reported as one.
        linker = self.linker(
            monkeypatch, self.response(400, {"status": "ERROR", "statusMessage": "Bad field"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await linker._get_dedup_ids("mzk.MZK01-000471470")

    async def test_dedup_group_survives_one_unloadable_member(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        linker, comparator, _ = linker_with_dedup(
            monkeypatch,
            ["caslin.SKC01-000000000", "caslin.SKC01-001217729"],
            [0.9],
        )

        records = iter([None, marc_record("skc2")])

        async def fake_record(id: str) -> MarcRecord | None:
            return next(records)

        monkeypatch.setattr(linker, "_get_record", fake_record)

        link = await run_linker(linker)

        assert link is not None
        assert link.system_number == "001217729"
        assert comparator.compared == 1

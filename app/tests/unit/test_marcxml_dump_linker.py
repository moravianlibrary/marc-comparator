"""Retrieval keys, dump parsing and the comparator gate of the SKC linker."""

import gzip
import re
from typing import cast

import httpx
import pytest
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]  # lxml ships no stubs
from marc_comparator.authority_linkers.marcxml_dump_linker import (
    DumpIdentifier,
    MarcXmlDumpLinker,
    MarcXmlDumpLinkerConfig,
    _dump_edition,
    _DumpStream,
    _fold,
    _normalize_isbn,
    _parse_dump_record,
    _record_identifiers,
    _reject_unreadable_dump,
    _SystemNumberSpec,
)
from marc_comparator.comparators import RecordComparisonResult
from marc_comparator.harvest import HarvestStorageUnavailable
from marcdantic import MarcRecord

MARC_XML = """
<record xmlns="http://www.loc.gov/MARC21/slim">
  <leader>     nam a22      a 4500</leader>
  <controlfield tag="001">kzp00001</controlfield>
  <controlfield tag="005">20170113091406.0</controlfield>
  <controlfield tag="008">120529s2012    xr a   f f    000 0 cze d</controlfield>
  <datafield tag="015" ind1=" " ind2=" ">
    <subfield code="a">cnb002370652</subfield>
  </datafield>
  <datafield tag="020" ind1=" " ind2=" ">
    <subfield code="a">978-80-87186-82-4 (bro&#382;.)</subfield>
  </datafield>
  <datafield tag="035" ind1=" " ind2=" ">
    <subfield code="a">(OCoLC)0798996181</subfield>
  </datafield>
  <datafield tag="100" ind1="1" ind2=" ">
    <subfield code="a">Drozd, Zden&#283;k,</subfield>
  </datafield>
  <datafield tag="245" ind1="0" ind2="0">
    <subfield code="a">Elektromagnetick&#233; z&#225;&#345;en&#237; :</subfield>
    <subfield code="b">vzd&#283;l&#225;vac&#237; modul fyzika</subfield>
  </datafield>
  <datafield tag="856" ind1="4" ind2=" ">
    <subfield code="u">http://www.digitalniknihovna.cz/mzk/uuid/uuid:09ac4b40-cb1c-11e9-b223-005056827e52</subfield>
  </datafield>
  <datafield tag="998" ind1=" " ind2=" ">
    <subfield code="a">http://aleph.nkp.cz/F/?func=direct&amp;doc_number=000123456&amp;local_base=SKC</subfield>
  </datafield>
</record>
"""


#: The default, Aleph-style reading of a record's own system number.
ALEPH_SPEC = _SystemNumberSpec.of(MarcXmlDumpLinkerConfig())


def marc_record() -> MarcRecord:
    return MarcRecord.from_xml(etree.fromstring(MARC_XML.strip().encode()))


class ScriptedComparator:
    """Return a prepared score per candidate, in the order they are compared."""

    def __init__(self, scores: list[float]) -> None:
        self.scores = list(scores)
        self.compared = 0

    async def run(self, record_a: MarcRecord, record_b: MarcRecord) -> RecordComparisonResult:
        score = self.scores[self.compared]
        self.compared += 1
        return RecordComparisonResult(overall_score=score)


def linker_with_candidates(
    monkeypatch: pytest.MonkeyPatch, scores: list[float], **config: object
) -> tuple[MarcXmlDumpLinker, ScriptedComparator]:
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig(**config))  # pyright: ignore[reportArgumentType]
    comparator = ScriptedComparator(scores)
    linker._comparator = cast(object, comparator)  # pyright: ignore[reportAttributeAccessIssue]
    linker.bind_harvest_storage(
        cast(object, object())  # pyright: ignore[reportArgumentType]
    )

    candidates = [
        type("Candidate", (), {"sysno": f"00000000{index}", "record": marc_record()})()
        for index in range(len(scores))
    ]
    monkeypatch.setattr(MarcXmlDumpLinker, "_candidates", lambda self, record, key=None: candidates)
    return linker, comparator


def test_fold_ignores_diacritics_punctuation_and_spacing():
    assert _fold("Elektromagnetické záření :") == _fold("elektromagneticke  zareni")


def test_fold_keeps_non_latin_words():
    # A wiped key would silently drop every foreign-script title out of the
    # title fallback, so folding must not be Latin-only.
    assert _fold("Война и миръ") == "воина и миръ"


def test_isbn_drops_the_qualifier_catalogues_append():
    assert _normalize_isbn("978-80-87186-82-4 (brož.)") == "9788087186824"
    assert _normalize_isbn("80-7185-612-X") == "807185612X"
    assert _normalize_isbn("   ") is None


@pytest.mark.parametrize("value", ["(brož.)", "(", "brož.", "", "   ", "()"])
def test_isbn_subfield_holding_only_a_qualifier_is_not_fatal(value: str):
    # Real dumps carry 020$a with the qualifier and no number. Indexing the
    # split of that raised IndexError, and one such record in ten million ended
    # the entire harvest an hour in.
    assert _normalize_isbn(value) is None


def test_parse_dump_record_reads_keys_and_keeps_the_marc():
    parsed = _parse_dump_record(etree.fromstring(MARC_XML.strip().encode()), ALEPH_SPEC)

    assert parsed is not None
    # The system number is the one in 998$a, not the contributing library's 001.
    assert parsed.sysno == "000123456"
    assert parsed.year == 2012
    assert parsed.title_key == _fold("Elektromagnetické záření")
    assert parsed.author_key == _fold("Drozd, Zdeněk")

    restored = MarcRecord.from_xml(etree.fromstring(_inflate(parsed.marc)))
    assert restored.variable_fields.root["015"][0].subfields["a"] == ["cnb002370652"]
    # The app stores the linked record from its raw MARC bytes, which only a
    # record parsed from XML or MRC carries.
    assert restored._marc


def test_parse_dump_record_skips_records_without_a_system_number():
    without_998 = MARC_XML.replace("998", "997")
    assert _parse_dump_record(etree.fromstring(without_998.strip().encode()), ALEPH_SPEC) is None


def test_dump_and_record_identifiers_agree():
    # Retrieval only works if both sides normalize the same way, so compare the
    # keys extracted from the dump against those taken from the parsed record.
    parsed = _parse_dump_record(etree.fromstring(MARC_XML.strip().encode()), ALEPH_SPEC)
    assert parsed is not None

    from_dump: dict[DumpIdentifier, set[str]] = {}
    for kind, value in parsed.identifiers:
        from_dump.setdefault(kind, set()).add(value)

    assert from_dump == _record_identifiers(marc_record())
    assert from_dump == {
        DumpIdentifier.Cnb: {"cnb002370652"},
        DumpIdentifier.Isbn: {"9788087186824"},
        DumpIdentifier.Oclc: {"798996181"},
        DumpIdentifier.Uuid: {"uuid:09ac4b40-cb1c-11e9-b223-005056827e52"},
    }


def test_dump_stream_reads_every_concatenated_member():
    # A dump written by a parallel compressor arrives as several members; stopping
    # at the first would publish a truncated catalogue as a complete one.
    stream = _DumpStream()
    members = gzip.compress(b"<a>first</a>") + gzip.compress(b"<b>second</b>")
    assert stream.feed(members) == b"<a>first</a><b>second</b>"
    assert stream.inflating is True


def test_dump_stream_passes_through_a_body_the_transport_already_inflated():
    # aleph.nkp.cz sends Content-Encoding: x-gzip, which httpx normalizes and
    # inflates itself, so the dump arrives here as plain XML. Inflating it a
    # second time fails with "incorrect header check" and no harvest happens.
    stream = _DumpStream()

    assert (
        stream.feed(b"<collection><record/></collection>") == b"<collection><record/></collection>"
    )
    assert stream.inflating is False


def test_dump_stream_waits_for_enough_bytes_to_recognize_gzip():
    # A first chunk of one byte must not be mistaken for plain XML.
    stream = _DumpStream()
    compressed = gzip.compress(b"<a>first</a>")

    assert stream.feed(compressed[:1]) == b""
    assert stream.inflating is None
    assert stream.feed(compressed[1:]) == b"<a>first</a>"
    assert stream.inflating is True


def test_dump_edition_prefers_the_etag():
    headers = httpx.Headers({"etag": '"abc"', "last-modified": "Tue, 22 Sep 2026 00:29:23 GMT"})
    assert _dump_edition(headers) == '"abc"'
    assert _dump_edition(httpx.Headers({"last-modified": "Tue, 22 Sep 2026 00:29:23 GMT"})) == (
        "Tue, 22 Sep 2026 00:29:23 GMT"
    )
    assert _dump_edition(httpx.Headers({})) is None


def test_source_identity_follows_the_dump_but_not_the_thresholds():
    baseline = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig()).harvest_source_identity()

    assert (
        MarcXmlDumpLinker(MarcXmlDumpLinkerConfig(minimum_confidence=0.5)).harvest_source_identity()
        == baseline
    )
    assert (
        MarcXmlDumpLinker(
            MarcXmlDumpLinkerConfig(dump_url="https://example.test/skc.xml.gz")
        ).harvest_source_identity()
        != baseline
    )


@pytest.mark.asyncio
async def test_run_refuses_rather_than_reporting_no_link_without_local_data():
    # The caller deletes links it no longer finds, so an unavailable dataset must
    # not look like an answer.
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    with pytest.raises(HarvestStorageUnavailable):
        await linker.run("MZK01", "000123456", marc_record(), "SKC")


@pytest.mark.asyncio
async def test_run_rejects_a_target_base_it_does_not_serve():
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    with pytest.raises(ValueError):
        await linker.run("MZK01", "000123456", marc_record(), "KNAV")


@pytest.mark.asyncio
async def test_run_keeps_the_best_scoring_candidate(monkeypatch):
    linker, comparator = linker_with_candidates(monkeypatch, [0.91, 0.97, 0.93])

    link = await linker.run("MZK01", "000123456", marc_record(), "SKC")

    assert link is not None
    assert link.system_number == "000000001"
    assert link.confidence == 0.97
    assert link.base == "SKC"
    assert comparator.compared == 3


@pytest.mark.asyncio
async def test_run_reports_a_plausible_match_with_its_real_score(monkeypatch):
    # Reporting the score rather than a yes/no is what lets the caller weigh
    # this linker against another when neither is certain.
    linker, _ = linker_with_candidates(monkeypatch, [0.72, 0.85])

    link = await linker.run("MZK01", "000123456", marc_record(), "SKC")

    assert link is not None
    assert link.confidence == 0.85


@pytest.mark.asyncio
async def test_run_stays_silent_below_the_minimum(monkeypatch):
    linker, _ = linker_with_candidates(monkeypatch, [0.69, 0.55])

    assert await linker.run("MZK01", "000123456", marc_record(), "SKC") is None


@pytest.mark.asyncio
async def test_minimum_is_inclusive(monkeypatch):
    linker, _ = linker_with_candidates(monkeypatch, [0.7])

    link = await linker.run("MZK01", "000123456", marc_record(), "SKC")

    assert link is not None
    assert link.confidence == 0.7


def _inflate(data: bytes) -> bytes:
    import zlib

    return zlib.decompress(data)


class TestGenericSystemNumbers:
    """The one thing that differs between catalogues publishing a MARC dump."""

    def test_aleph_deep_link_is_the_default(self):
        parsed = _parse_dump_record(etree.fromstring(MARC_XML.strip().encode()), ALEPH_SPEC)

        assert parsed is not None
        # Padded, so a number stored now matches a link written earlier.
        assert parsed.sysno == "000123456"

    def test_a_catalogue_publishing_its_control_number_reads_001(self):
        # The common case for a single library: no deep link anywhere, the
        # record's own number sits in 001. That is a control field, which has no
        # subfields, so the whole text is the value. Padding still applies, and
        # a catalogue whose numbers are not purely numeric turns it off.
        spec = _SystemNumberSpec.of(
            MarcXmlDumpLinkerConfig(system_number_tag="001", system_number_pattern=None)
        )

        parsed = _parse_dump_record(etree.fromstring(MARC_XML.strip().encode()), spec)

        assert parsed is not None
        assert parsed.sysno == "0kzp00001"

    def test_padding_can_be_switched_off(self):
        spec = _SystemNumberSpec.of(
            MarcXmlDumpLinkerConfig(
                system_number_tag="001", system_number_pattern=None, system_number_padding=0
            )
        )

        parsed = _parse_dump_record(etree.fromstring(MARC_XML.strip().encode()), spec)

        assert parsed is not None
        assert parsed.sysno == "kzp00001"

    def test_a_record_without_the_configured_field_is_skipped(self):
        # Not an error: a dump may carry records this catalogue cannot address.
        spec = _SystemNumberSpec.of(MarcXmlDumpLinkerConfig(system_number_tag="907"))

        assert _parse_dump_record(etree.fromstring(MARC_XML.strip().encode()), spec) is None

    def test_the_system_number_field_can_also_be_a_retrieval_field(self):
        # 245 carries the title and would be the system number source here; one
        # read must not shadow the other.
        spec = _SystemNumberSpec.of(
            MarcXmlDumpLinkerConfig(
                system_number_tag="245",
                system_number_subfield="a",
                system_number_pattern=None,
                system_number_padding=0,
            )
        )

        parsed = _parse_dump_record(etree.fromstring(MARC_XML.strip().encode()), spec)

        assert parsed is not None
        assert parsed.sysno == "Elektromagnetické záření :"
        assert parsed.title_key == _fold("Elektromagnetické záření")

    def test_reading_the_number_differently_is_a_different_dataset(self):
        # The host binds a harvested copy only when the fingerprint matches, and
        # these settings change what every row is keyed by.
        baseline = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig()).harvest_source_identity()

        for changed in (
            MarcXmlDumpLinkerConfig(system_number_tag="001"),
            MarcXmlDumpLinkerConfig(system_number_subfield="b"),
            MarcXmlDumpLinkerConfig(system_number_pattern=None),
            MarcXmlDumpLinkerConfig(system_number_padding=0),
        ):
            assert MarcXmlDumpLinker(changed).harvest_source_identity() != baseline

    def test_an_unreadable_pattern_fails_at_construction(self):
        # Rather than part-way through an hour-long harvest.
        with pytest.raises(re.error):
            MarcXmlDumpLinker(MarcXmlDumpLinkerConfig(system_number_pattern="(unclosed"))


class TestDumpFormat:
    def test_a_marcxml_dump_is_accepted(self):
        assert _reject_unreadable_dump(b'<?xml version="1.0"?><collection>') is None
        assert _reject_unreadable_dump(b"  \n<collection/>") is None

    def test_an_iso2709_dump_is_named_rather_than_left_to_the_xml_parser(self):
        with pytest.raises(ValueError, match="ISO 2709"):
            _reject_unreadable_dump(b"00241nam a2200085   4500001000900000")

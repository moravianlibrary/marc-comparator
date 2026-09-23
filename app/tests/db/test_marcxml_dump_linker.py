"""The SKC harvest fills real tables and linking reads them without a network."""

import asyncio
import gzip
from typing import cast

import httpx
import pytest
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]  # lxml ships no stubs
from marc_comparator.authority_linkers.marcxml_dump_linker import (
    IDENTIFIERS_TABLE,
    RECORDS_TABLE,
    MarcXmlDumpLinker,
    MarcXmlDumpLinkerConfig,
)
from marc_comparator.comparators import RecordComparisonResult
from marc_comparator.harvest import HarvestContext, HarvestStorage
from marcdantic import MarcRecord
from sqlalchemy import text

pytestmark = pytest.mark.db

SCHEMA = "plugin_marcxml_dump_linker_test"
ETAG = '"first-edition"'

#: Captured before any patching, so serving a second dump within one test does
#: not wrap an already-patched client.
REAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def run_thread_calls_inline(monkeypatch):
    """The restricted test sandbox cannot start executor threads."""

    async def inline(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", inline)


def dump_record(
    sysno: str,
    *,
    title: str,
    isbn: str | None = None,
    cnb: str | None = None,
    author: str = "Drozd, Zdeněk",
    year: str = "2012",
    standalone: bool = False,
) -> str:
    # Records inside the dump inherit the namespace from <collection>; storing
    # them has to carry it along, or nothing would re-parse on lookup.
    namespace = ' xmlns="http://www.loc.gov/MARC21/slim"' if standalone else ""
    identifiers = ""
    if cnb:
        identifiers += f'<datafield tag="015" ind1=" " ind2=" "><subfield code="a">{cnb}</subfield></datafield>'
    if isbn:
        identifiers += f'<datafield tag="020" ind1=" " ind2=" "><subfield code="a">{isbn}</subfield></datafield>'
    return f"""
  <record{namespace}>
    <leader>     nam a22      a 4500</leader>
    <controlfield tag="001">kzp{sysno}</controlfield>
    <controlfield tag="005">20170113091406.0</controlfield>
    <controlfield tag="008">120529s{year}    xr a   f f    000 0 cze d</controlfield>
    {identifiers}
    <datafield tag="100" ind1="1" ind2=" "><subfield code="a">{author}</subfield></datafield>
    <datafield tag="245" ind1="0" ind2="0"><subfield code="a">{title}</subfield></datafield>
    <datafield tag="998" ind1=" " ind2=" ">
      <subfield code="a">http://aleph.nkp.cz/F/?func=direct&amp;doc_number={sysno}&amp;local_base=SKC</subfield>
    </datafield>
  </record>"""


def dump(*records: str) -> bytes:
    collection = (
        '<collection xmlns="http://www.loc.gov/MARC21/slim">' + "".join(records) + "</collection>"
    )
    return gzip.compress(collection.encode())


def query_record(*, isbn: str | None = None, cnb: str | None = None, title: str) -> MarcRecord:
    return MarcRecord.from_xml(
        etree.fromstring(
            dump_record("000000999", title=title, isbn=isbn, cnb=cnb, standalone=True)
            .strip()
            .encode()
        )
    )


def serve(monkeypatch, body: bytes, *, etag: str = ETAG) -> None:
    """Answer the dump request from memory, leaving the plugin's code untouched."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"etag": etag}, content=body)

    def factory(**kwargs):
        return REAL_ASYNC_CLIENT(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.fixture
def harvest_engine(db_engine):
    with db_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{SCHEMA}"'))
        MarcXmlDumpLinker.harvest_metadata(SCHEMA).create_all(connection)
    yield db_engine
    with db_engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{SCHEMA}" CASCADE'))


async def harvest(linker: MarcXmlDumpLinker, engine, watermark: str | None = None):
    progress: list[tuple[int, int | None]] = []
    with engine.begin() as connection:
        result = await linker.harvest(
            HarvestContext(
                connection=connection,
                schema=SCHEMA,
                progress=lambda done, total=None: progress.append((done, total)),
                watermark=watermark,
            )
        )
    return result, progress


def ready_linker(engine, scores: dict[str, float] | None = None) -> MarcXmlDumpLinker:
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    linker.bind_harvest_storage(
        HarvestStorage(
            schema=SCHEMA,
            source_identity=linker.harvest_source_identity(),
            connection=engine.connect,
        )
    )
    if scores is not None:
        linker._comparator = cast(  # pyright: ignore[reportAttributeAccessIssue]
            object, ScoreBySysno(scores, linker)
        )
    return linker


class ScoreBySysno:
    """Score a comparison by which harvested record it is against."""

    def __init__(self, scores: dict[str, float], linker: MarcXmlDumpLinker) -> None:
        self.scores = scores
        self.linker = linker

    async def run(self, record_a: MarcRecord, record_b: MarcRecord) -> RecordComparisonResult:
        sysno = record_b.variable_fields.root["998"][0].subfields["a"][0].split("doc_number=")[1]
        return RecordComparisonResult(overall_score=self.scores.get(sysno.split("&")[0], 0.0))


@pytest.mark.asyncio
async def test_identifier_lookup_finds_the_record_without_a_network_call(
    harvest_engine, monkeypatch
):
    serve(
        monkeypatch,
        dump(
            dump_record("000000001", title="Elektromagnetické záření :", isbn="978-80-87186-82-4"),
            dump_record("000000002", title="Něco jiného", cnb="cnb002370652"),
        ),
    )
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    result, progress = await harvest(linker, harvest_engine)

    assert result.records == 2
    assert result.watermark == ETAG
    assert progress[-1][0] > 0
    with harvest_engine.begin() as connection:
        assert connection.scalar(text(f"SELECT count(*) FROM {SCHEMA}.{RECORDS_TABLE}")) == 2
        assert connection.scalar(text(f"SELECT count(*) FROM {SCHEMA}.{IDENTIFIERS_TABLE}")) == 2
        # Dropped for the bulk load, so they have to come back with it.
        indexes = connection.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = :schema"), {"schema": SCHEMA}
        ).scalars()
        assert "ix_marcxml_dump_records_title_key" in set(indexes)

    linked = ready_linker(harvest_engine, {"000000001": 0.95})
    link = await linked.run(
        "MZK01",
        "000000999",
        query_record(isbn="978-80-87186-82-4 (brož.)", title="Elektromagnetické záření :"),
        "SKC",
    )

    assert link is not None
    assert link.system_number == "000000001"
    assert link.confidence == 0.95
    # The app stores the linked record from its raw MARC bytes.
    assert link.record._marc


@pytest.mark.asyncio
async def test_title_fallback_applies_only_without_identifier_hits(harvest_engine, monkeypatch):
    serve(
        monkeypatch,
        dump(
            dump_record("000000010", title="Sborník prací"),
            dump_record("000000011", title="Sborník prací", year="1998"),
        ),
    )
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    assert (await harvest(linker, harvest_engine))[0].records == 2

    linked = ready_linker(harvest_engine, {"000000010": 0.93, "000000011": 0.91})
    link = await linked.run("MZK01", "000000999", query_record(title="Sborník prací"), "SKC")

    assert link is not None
    assert link.system_number == "000000010"


@pytest.mark.asyncio
async def test_unrelated_record_finds_nothing(harvest_engine, monkeypatch):
    serve(monkeypatch, dump(dump_record("000000020", title="Sborník prací")))
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    await harvest(linker, harvest_engine)

    linked = ready_linker(harvest_engine, {"000000020": 1.0})

    assert await linked.run(
        "MZK01", "000000999", query_record(title="Úplně jiný název"), "SKC"
    ) is (None)


@pytest.mark.asyncio
async def test_unchanged_edition_keeps_the_previous_copy(harvest_engine, monkeypatch):
    serve(monkeypatch, dump(dump_record("000000030", title="Sborník prací", cnb="cnb000000030")))
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    first, _ = await harvest(linker, harvest_engine)

    # Same edition, empty body: reading it would parse to nothing, so an
    # unchanged result proves the download was skipped rather than repeated.
    serve(monkeypatch, b"", etag=ETAG)
    second, _ = await harvest(linker, harvest_engine, watermark=first.watermark)

    assert second.records == first.records == 1
    assert second.watermark == ETAG
    with harvest_engine.begin() as connection:
        assert connection.scalar(text(f"SELECT count(*) FROM {SCHEMA}.{RECORDS_TABLE}")) == 1


@pytest.mark.asyncio
async def test_new_edition_replaces_the_previous_copy(harvest_engine, monkeypatch):
    serve(monkeypatch, dump(dump_record("000000040", title="Staré vydání", cnb="cnb000000040")))
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())
    first, _ = await harvest(linker, harvest_engine)

    serve(
        monkeypatch,
        dump(dump_record("000000041", title="Nové vydání", cnb="cnb000000041")),
        etag='"second-edition"',
    )
    second, _ = await harvest(linker, harvest_engine, watermark=first.watermark)

    assert second.records == 1
    with harvest_engine.begin() as connection:
        remaining = connection.execute(
            text(f"SELECT sysno FROM {SCHEMA}.{RECORDS_TABLE}")
        ).scalars()
        assert list(remaining) == ["000000041"]


@pytest.mark.asyncio
async def test_truncated_dump_fails_instead_of_publishing_a_partial_catalogue(
    harvest_engine, monkeypatch
):
    complete = dump(dump_record("000000050", title="Sborník prací"))
    serve(monkeypatch, gzip.compress(gzip.decompress(complete)[:-40]))
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())

    with pytest.raises(etree.XMLSyntaxError):
        await harvest(linker, harvest_engine)


@pytest.mark.asyncio
async def test_dump_the_transport_already_inflated_is_harvested(harvest_engine, monkeypatch):
    # aleph.nkp.cz serves the dump with Content-Encoding: x-gzip, so httpx hands
    # over plain XML. Inflating it again failed the harvest before it read a row.
    collection = gzip.decompress(
        dump(dump_record("000000060", title="Rozbalený dump", cnb="cnb000000060"))
    )
    serve(monkeypatch, collection)
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())

    result, _ = await harvest(linker, harvest_engine)

    assert result.records == 1
    with harvest_engine.begin() as connection:
        assert connection.scalar(text(f"SELECT count(*) FROM {SCHEMA}.{RECORDS_TABLE}")) == 1


@pytest.mark.asyncio
async def test_a_binary_marc_dump_says_so_instead_of_failing_as_bad_xml(
    harvest_engine, monkeypatch
):
    # Catalogues publish ISO 2709 and MARCXML side by side, so pointing at the
    # wrong one is an ordinary mistake. Fed to the XML parser it would surface
    # as a syntax error, which reads like a corrupted download.
    serve(monkeypatch, b"00241nam a2200085   4500001000900000\x1e000000001\x1e\x1d")
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())

    with pytest.raises(ValueError, match="ISO 2709"):
        await harvest(linker, harvest_engine)


@pytest.mark.asyncio
async def test_records_straddling_a_parser_feed_boundary_survive(
    harvest_engine, monkeypatch, request
):
    # A compressed chunk inflates to many times its size, so the document is fed
    # to the parser in bounded slices. Those boundaries fall mid-record, and a
    # record split across two feeds must still arrive whole.
    monkeypatch.setattr("marc_comparator.authority_linkers.marcxml_dump_linker.PARSE_FEED_SIZE", 64)
    serve(
        monkeypatch,
        dump(
            *(
                dump_record(f"00000010{n}", title=f"Svazek {n}", cnb=f"cnb00000010{n}")
                for n in range(5)
            )
        ),
    )
    linker = MarcXmlDumpLinker(MarcXmlDumpLinkerConfig())

    result, _ = await harvest(linker, harvest_engine)

    assert result.records == 5
    with harvest_engine.begin() as connection:
        titles = connection.execute(
            text(f"SELECT title_key FROM {SCHEMA}.{RECORDS_TABLE} ORDER BY sysno")
        ).scalars()
        assert list(titles) == [f"svazek {n}" for n in range(5)]

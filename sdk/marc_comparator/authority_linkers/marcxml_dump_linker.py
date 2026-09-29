"""Linking against a local copy of a catalogue published as a MARC dump.

Some catalogues publish their entire contents as one downloadable gzipped
MARC21 XML file — the Czech union catalogue (SKC) does, under CC0, and the
defaults here point at it. Nothing below is specific to that catalogue:
anything published the same way works, which is why the one field that differs
between publishers, where a record carries its own system number, is
configuration rather than a constant.

Copying the dump into plugin-owned tables turns linking into indexed database
lookups, so no request leaves the machine while a linking task runs — the
alternative, one or two HTTP calls per record against someone else's service,
sets the pace of every batch and fails with it.

Candidates are retrieved identifiers-first and by title only as a fallback, but
retrieval never decides anything on its own: what a candidate is worth comes
from running the MARC comparator over both records. Retrieval is allowed to be
generous because the score is what survives.

The reported confidence is that score, so the caller can tell a certain match
from a plausible one. What the linker declines to report at all depends on how
the candidate was found: a pair sharing an identifier is the same work whatever
it scores, while a pair sharing only a title is nothing until the score says
otherwise, so the two have separate floors.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import unicodedata
import zlib
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import httpx
from lxml import etree
from marcdantic import MarcRecord
from marcdantic.selectors import IsbnActiveJq, IssnActiveJq, NbnActiveJq, TitleJq
from pydantic import BaseModel, Field

from ..comparators import RecordComparisonResult
from ..comparators.default import DefaultComparator, DefaultComparatorConfig
from ..harvest import HarvestContext, HarvestResult, HarvestStorageUnavailable
from ._base import AuthorityLink, BaseAuthorityLinker, LinkRequest, MatchRoute

if TYPE_CHECKING:
    from sqlalchemy import Connection, Index, MetaData, Table

logger = logging.getLogger(__name__)

RECORDS_TABLE = "records"
IDENTIFIERS_TABLE = "identifiers"

#: Rows buffered before a write. Small enough that a batch of MARC blobs stays
#: a few megabytes, large enough that 10M records are not 10M round trips.
HARVEST_BATCH_SIZE = 2000
_GZIP_MAGIC = b"\x1f\x8b"
#: An ISO 2709 record opens with a five-digit record length. That is the other
#: common way a catalogue publishes a dump, and this linker cannot read it — so
#: it is recognised in order to say so rather than fail as malformed XML.
_ISO2709_LEADER = re.compile(rb"^\d{5}[a-z ]")

#: Compressed bytes pulled from the network per read.
DOWNLOAD_CHUNK_SIZE = 1 << 20

#: Decompressed bytes handed to the XML parser per feed. Independent of the
#: download chunk because the ratio between them is the publisher's choice: this
#: dump inflates roughly elevenfold, and one whole chunk at a time exceeds what
#: libxml2 accepts into its push buffer.
PARSE_FEED_SIZE = 1 << 20

#: The dump is a single ~2.6 GB response, so a read timeout bounds one chunk,
#: never the transfer. Without an explicit timeout httpx would give up on the
#: whole download after five seconds.
DUMP_TIMEOUT = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)

#: Ask for the file as stored rather than as a transfer-encoded body.
#:
#: aleph.nkp.cz announces the dump as ``Content-Encoding: x-gzip``. Left to its
#: default, httpx treats that as a transfer encoding and inflates the body, so
#: the bytes read are the XML inside while Content-Length still describes the
#: compressed file — the two are no longer comparable and the progress bar has
#: no denominator. Requesting identity makes the transport hand over the file
#: untouched: this module inflates it, and bytes read then count against
#: Content-Length exactly.
_DUMP_REQUEST_HEADERS = {"Accept-Encoding": "identity"}


class DumpIdentifier(StrEnum):
    """Identifier kinds a record can be found by, most trusted first.

    The order decides which candidates survive the per-record cap when a record
    matches several ways; it is not a confidence score. The comparator gate
    still judges every candidate that gets through.
    """

    Cnb = "cnb"
    Uuid = "uuid"
    Oclc = "oclc"
    Isbn = "isbn"
    Issn = "issn"


_IDENTIFIER_PRIORITY = {kind: position for position, kind in enumerate(DumpIdentifier)}

_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
_OCLC_NUMBER = re.compile(r"^\(OCoLC\)0*(\d+)$")
_UUID = re.compile(
    r"uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
#: Aleph-published dumps carry the catalogue's own system number in 998$a, as a
#: deep link; field 001 there holds the identifier of whichever library
#: contributed the record. Other publishers put it elsewhere, so this is only
#: the default of ``system_number_pattern``.
_ALEPH_DOC_NUMBER = r"doc_number=(\d+)"

_CONTROL_FIELD_008 = "008"
#: Tags read for retrieval keys. The tag carrying the system number is added per
#: configuration, since which one that is depends on who published the dump.
_HARVESTED_TAGS = frozenset({"015", "020", "022", "035", "100", "110", "245", "856"})


class MarcXmlDumpLinkerConfig(BaseModel):
    #: Where the published dump is downloaded from. The default is the Czech
    #: union catalogue; any catalogue publishing a MARC21 XML collection the
    #: same way works, gzipped or not.
    dump_url: str = "https://aleph.nkp.cz/data/skc.xml.gz"
    #: The authority base links are recorded under.
    target_base: str = "SKC"

    #: Which field carries the record's system number in the published dump —
    #: the number that identifies it in the catalogue it came from, and the one
    #: a link is written with. This is the single thing that differs between
    #: publishers: Aleph dumps put a deep link in 998$a, while a catalogue that
    #: publishes its own control number sets this to "001" and clears the
    #: pattern. Control fields are read whole; the subfield is ignored for them.
    system_number_tag: str = Field(default="998", min_length=3, max_length=3)
    system_number_subfield: str = Field(default="a", min_length=1, max_length=1)
    #: Regular expression pulling the number out of that field's text. The first
    #: capturing group wins, or the whole match when there is none. Empty means
    #: the field already holds nothing but the number.
    system_number_pattern: str | None = _ALEPH_DOC_NUMBER
    #: Left-pad the extracted number to this width, so the dump and a link
    #: written earlier agree on "123" versus "000000123". 0 stores it verbatim.
    system_number_padding: int = Field(default=9, ge=0, le=16)
    #: Lowest score worth reporting for a candidate both catalogues give the
    #: same identifier. Retrieval has already answered "same work" here, so the
    #: score is not evidence about whether the link is real — it measures how
    #: far the two descriptions have drifted, and a low one is the most useful
    #: thing this linker can report rather than a reason to say nothing. The
    #: default keeps every one of them; raise it to hide the noisy tail.
    identifier_minimum_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    #: Lowest score worth reporting for a candidate found only by its title.
    #: Nothing here has established the two records are the same work, so the
    #: score is the only evidence there is, and generic titles produce
    #: plausible-looking candidates in quantity. 0.55 is what two unrelated
    #: records score.
    title_minimum_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    #: Candidates compared per record. Retrieval by title alone can return many
    #: rows for a generic title, and every candidate costs a full comparison.
    candidate_limit: int = Field(default=10, ge=1, le=100)


@dataclass(frozen=True, slots=True)
class _SystemNumberSpec:
    """How to read a record's own system number out of one publisher's dump."""

    tag: str
    subfield: str
    pattern: re.Pattern[str] | None
    padding: int

    @classmethod
    def of(cls, config: MarcXmlDumpLinkerConfig) -> _SystemNumberSpec:
        raw = config.system_number_pattern
        return cls(
            tag=config.system_number_tag,
            subfield=config.system_number_subfield,
            pattern=re.compile(raw) if raw else None,
            padding=config.system_number_padding,
        )

    @property
    def is_control_field(self) -> bool:
        # MARC21 reserves 001-009 for control fields, which have no subfields.
        return self.tag < "010"

    @property
    def harvested_tags(self) -> frozenset[str]:
        return _HARVESTED_TAGS if self.is_control_field else _HARVESTED_TAGS | {self.tag}

    def extract(self, value: str) -> str | None:
        if self.pattern is None:
            found = value.strip()
        else:
            match = self.pattern.search(value)
            if match is None:
                return None
            found = (match.group(1) if match.groups() else match.group(0)).strip()
        if not found:
            return None
        return found.zfill(self.padding) if self.padding else found


@dataclass(frozen=True, slots=True)
class _Candidate:
    sysno: str
    record: MarcRecord


@dataclass(frozen=True, slots=True)
class _Retrieval:
    """One record's candidates, and which of the two paths produced them.

    Retrieval takes the identifier path or the title path, never both, so the
    route belongs to the attempt rather than to each candidate.
    """

    route: MatchRoute | None
    candidates: list[_Candidate]


@dataclass(slots=True)
class _ParsedRecord:
    """One dump record reduced to what retrieval needs, plus the MARC itself."""

    sysno: str
    title_key: str | None
    author_key: str | None
    year: int | None
    marc: bytes
    identifiers: list[tuple[DumpIdentifier, str]]


def _fold(value: str) -> str:
    """Lowercase, drop diacritics and punctuation, collapse whitespace.

    Both sides of a title comparison go through this, so the dump and the record
    being linked have to agree exactly — hence one function, never two.
    """

    decomposed = unicodedata.normalize("NFKD", value)
    letters = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _WHITESPACE.sub(" ", _NON_WORD.sub(" ", letters.lower())).strip()


def _normalize_isbn(value: str) -> str | None:
    """Strip the qualifier some catalogues append to 020$a ("… (brož.)").

    Real dumps contain 020$a holding nothing but the qualifier — "(brož.)" with
    the number missing. Splitting that leaves no tokens at all, so the head of
    the split is taken defensively rather than by index: one such record in ten
    million would otherwise end the whole harvest.
    """

    head, _, _ = value.strip().partition("(")
    token = next(iter(head.split()), "")
    normalized = re.sub(r"[^0-9Xx]", "", token).upper()
    return normalized or None


def _normalize_plain(value: str) -> str | None:
    normalized = re.sub(r"[^\w]", "", value).lower()
    return normalized or None


def _year_from_008(field: str | None) -> int | None:
    """Date 1 from the fixed-length data elements, when it is a plain year."""

    if field is None or len(field) < 11:
        return None
    candidate = field[7:11]
    return int(candidate) if candidate.isdigit() else None


def _dump_edition(headers: httpx.Headers) -> str | None:
    """Identify the published dump, so an unchanged one can be skipped.

    ETag is preferred; Last-Modified is the fallback. Returning None means the
    server told us nothing usable, and the dump is then always re-read.
    """

    etag = headers.get("etag")
    if etag:
        return etag.strip()
    last_modified = headers.get("last-modified")
    return last_modified.strip() if last_modified else None


def _reject_unreadable_dump(head: bytes) -> None:
    """Name the format when it is one this linker cannot read.

    Fed to the XML parser, an ISO 2709 dump fails somewhere in the middle as a
    syntax error, which reads like a corrupted download rather than the wrong
    file. Catalogues publish both forms side by side, so picking the wrong URL
    is an ordinary mistake and deserves an ordinary answer.
    """

    if _ISO2709_LEADER.match(head.lstrip()):
        raise ValueError(
            "The dump is ISO 2709 (binary MARC), which this linker cannot read. "
            "Point dump_url at the MARCXML form of the same dump."
        )


class _DumpStream:
    """Yield dump XML whether or not the transport already inflated it.

    The dump is a gzip file, and aleph.nkp.cz also announces it as
    ``Content-Encoding: x-gzip``. httpx reads that as a transfer encoding and
    inflates the body itself, so what arrives here is the XML that was inside
    the file. A server that serves the same file as an opaque download does no
    such thing and delivers gzip. The first two bytes settle which one this is;
    the headers have already proven they cannot.

    Gzip input may also be several concatenated members. A member boundary in
    the middle of the dump would otherwise end decoding silently, leaving a
    truncated catalogue that looks like a complete one.
    """

    def __init__(self) -> None:
        self._decompressor: zlib._Decompress | None = None
        self._head = b""
        #: None until enough bytes have arrived to tell.
        self.inflating: bool | None = None

    def feed(self, chunk: bytes) -> bytes:
        if self.inflating is None:
            self._head += chunk
            if len(self._head) < len(_GZIP_MAGIC):
                return b""
            chunk, self._head = self._head, b""
            self.inflating = chunk.startswith(_GZIP_MAGIC)
            if self.inflating:
                self._decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

        if not self.inflating:
            return chunk

        output = b""
        data = chunk
        while data:
            decompressor = self._decompressor
            if decompressor is None:  # pragma: no cover - set with self.inflating
                break
            output += decompressor.decompress(data)
            if not decompressor.eof:
                break
            data = decompressor.unused_data
            self._decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        return output


def _subfields(field: etree._Element) -> Iterator[tuple[str, str]]:
    for subfield in field:
        if etree.QName(subfield).localname != "subfield":
            continue
        code = subfield.get("code")
        text = (subfield.text or "").strip()
        if code and text:
            yield code, text


def _parse_dump_record(
    element: etree._Element, system_number: _SystemNumberSpec
) -> _ParsedRecord | None:
    """Extract retrieval keys and the MARC bytes from one dump record.

    Deliberately not routed through MarcRecord: building ten million validated
    models costs hours, and the model is only needed for the handful of
    candidates a lookup actually compares.
    """

    sysno: str | None = None
    title: str | None = None
    author: str | None = None
    field_008: str | None = None
    identifiers: list[tuple[DumpIdentifier, str]] = []
    harvested_tags = system_number.harvested_tags

    for child in element:
        tag_name = etree.QName(child).localname
        if tag_name == "controlfield":
            control_tag = child.get("tag")
            if control_tag == _CONTROL_FIELD_008:
                field_008 = child.text
            elif system_number.is_control_field and control_tag == system_number.tag and child.text:
                sysno = system_number.extract(child.text)
            continue
        if tag_name != "datafield":
            continue
        tag = child.get("tag")
        if tag not in harvested_tags:
            continue

        for code, value in _subfields(child):
            if tag == system_number.tag and code == system_number.subfield:
                sysno = system_number.extract(value) or sysno
            if tag == "245" and code == "a" and title is None:
                title = value
            elif tag in {"100", "110"} and code == "a" and author is None:
                author = value
            elif tag == "015" and code == "a":
                normalized = _normalize_plain(value)
                if normalized:
                    identifiers.append((DumpIdentifier.Cnb, normalized))
            elif tag == "020" and code == "a":
                normalized = _normalize_isbn(value)
                if normalized:
                    identifiers.append((DumpIdentifier.Isbn, normalized))
            elif tag == "022" and code == "a":
                normalized = _normalize_plain(value)
                if normalized:
                    identifiers.append((DumpIdentifier.Issn, normalized))
            elif tag == "035" and code == "a":
                match = _OCLC_NUMBER.match(value.strip())
                if match:
                    identifiers.append((DumpIdentifier.Oclc, match.group(1)))
            elif tag == "856" and code == "u":
                for found in _UUID.findall(value):
                    identifiers.append((DumpIdentifier.Uuid, found.lower()))

    if sysno is None:
        return None

    title_key = _fold(title) if title else None
    author_key = _fold(author) if author else None
    return _ParsedRecord(
        sysno=sysno,
        title_key=title_key or None,
        author_key=author_key or None,
        year=_year_from_008(field_008),
        # with_tail drops the whitespace between records, which is not part of
        # the record and would be stored ten million times over.
        marc=zlib.compress(etree.tostring(element, with_tail=False), 6),
        identifiers=identifiers,
    )


def _release(element: etree._Element) -> None:
    """Free the record and everything before it, bounding parser memory."""

    element.clear()
    parent = element.getparent()
    if parent is None:
        return
    while element.getprevious() is not None:
        del parent[0]


def _title_probe(record: MarcRecord) -> tuple[str, int | None, str | None]:
    """The normalized title to search on, and what orders its matches.

    Year and author only rank: a generic title matches many records, and
    narrowing on either would lose the right one whenever the two catalogues
    disagree about it.
    """

    titles = record.variable_fields.query(TitleJq) or []
    title_key = _fold(titles[0]) if titles else ""
    if not title_key:
        return "", None, None

    year = _year_from_008(record.fixed_fields.root.get(_CONTROL_FIELD_008))
    authors = [
        value
        for tag in ("100", "110")
        for field in record.variable_fields.root.get(tag, [])
        for value in field.subfields.get("a", [])
    ]
    return title_key, year, _fold(authors[0]) if authors else None


def _record_identifiers(record: MarcRecord) -> dict[DumpIdentifier, set[str]]:
    """The hard identifiers of the record being linked, normalized like the dump."""

    found: dict[DumpIdentifier, set[str]] = {}

    def collect(kind: DumpIdentifier, values: list[str] | None, normalize) -> None:
        for raw in values or []:
            normalized = normalize(raw)
            if normalized:
                found.setdefault(kind, set()).add(normalized)

    variable_fields = record.variable_fields
    collect(DumpIdentifier.Cnb, variable_fields.query(NbnActiveJq), _normalize_plain)
    collect(DumpIdentifier.Isbn, variable_fields.query(IsbnActiveJq), _normalize_isbn)
    collect(DumpIdentifier.Issn, variable_fields.query(IssnActiveJq), _normalize_plain)

    for field in variable_fields.root.get("035", []):
        for value in field.subfields.get("a", []):
            match = _OCLC_NUMBER.match(value.strip())
            if match:
                found.setdefault(DumpIdentifier.Oclc, set()).add(match.group(1))

    for field in variable_fields.root.get("856", []):
        for value in field.subfields.get("u", []):
            for uuid in _UUID.findall(value):
                found.setdefault(DumpIdentifier.Uuid, set()).add(uuid.lower())

    return found


class MarcXmlDumpLinker(BaseAuthorityLinker):
    """Link catalog records to the union catalogue from a harvested copy."""

    config_model = MarcXmlDumpLinkerConfig
    needs_harvest = True
    harvest_schema_version = 1

    def __init__(self, config: MarcXmlDumpLinkerConfig):
        self.config = config
        # Compiled once: the parser asks for it per record across a walk of
        # millions, and a bad pattern should fail here rather than mid-harvest.
        self._system_number = _SystemNumberSpec.of(config)
        # DefaultComparator writes the Ollama URL into module state when it is
        # constructed. The gate never calls the LLM, so carry the value already
        # in effect rather than resetting one the comparison feature configured
        # in this same worker process.
        from ..comparators.intiim_engine import llm

        self._comparator = DefaultComparator(
            DefaultComparatorConfig(
                ollama_url=llm.OLLAMA_URL,
                llm_enabled=False,
                nonstandard_llm_enabled=False,
            )
        )

        #: Rows for the window the host last announced, keyed by the record
        #: they belong to, and paired with the path that found them. Replaced
        #: wholesale by each prefetch, so it holds one window and not a run.
        #: Rows rather than parsed candidates: the MARC is kept compressed
        #: until the record it belongs to is reached.
        self._rows_cache: dict[tuple[str, str], tuple[MatchRoute | None, list[dict[str, Any]]]] = {}

    @classmethod
    async def get_target_bases(cls, config: MarcXmlDumpLinkerConfig) -> list[str]:
        return [config.target_base]

    def harvest_source_identity(self) -> str:
        """Fingerprint only what changes the copied dataset."""

        # How a system number is read decides what ends up stored under it, so
        # it belongs in the fingerprint as much as the source URL does.
        source = json.dumps(
            {
                "dump_url": self.config.dump_url,
                "system_number_tag": self.config.system_number_tag,
                "system_number_subfield": self.config.system_number_subfield,
                "system_number_pattern": self.config.system_number_pattern,
                "system_number_padding": self.config.system_number_padding,
            },
            sort_keys=True,
        )
        return hashlib.sha256(source.encode()).hexdigest()

    @classmethod
    def harvest_metadata(cls, schema: str) -> MetaData:
        """Declare the plugin-owned tables.

        SQLAlchemy stays an optional dependency for ordinary SDK and CLI use, so
        it is imported only where storage is actually described or touched.
        """

        from sqlalchemy import (
            Column,
            ForeignKey,
            Index,
            Integer,
            LargeBinary,
            MetaData,
            String,
            Table,
            Text,
        )

        metadata = MetaData(schema=schema)
        records = Table(
            RECORDS_TABLE,
            metadata,
            Column("sysno", String(16), primary_key=True),
            Column("title_key", Text),
            Column("author_key", Text),
            Column("year", Integer),
            # MARC21 XML as published, deflated. Stored whole because the
            # comparator gate and the resulting link both need the real record,
            # and re-fetching it per candidate would put the network back into
            # the linking loop.
            Column("marc", LargeBinary, nullable=False),
        )
        Index("ix_marcxml_dump_records_title_key", records.c.title_key)

        identifiers = Table(
            IDENTIFIERS_TABLE,
            metadata,
            Column(
                "sysno",
                String(16),
                ForeignKey(f"{schema}.{RECORDS_TABLE}.sysno", ondelete="CASCADE"),
                primary_key=True,
            ),
            Column("kind", String(8), primary_key=True),
            Column("value", Text, primary_key=True),
        )
        Index("ix_marcxml_dump_identifiers_kind_value", identifiers.c.kind, identifiers.c.value)
        return metadata

    async def harvest(self, ctx: HarvestContext) -> HarvestResult:
        """Replace the local copy from one published dump, inside ctx's transaction.

        The dump is a full snapshot with no incremental form, so a run either
        replaces everything or — when the published edition has not moved —
        keeps what is already there and does no work at all.

        Progress counts bytes read rather than records: the record count is
        unknown until the walk ends, and a multi-hour harvest with no percentage
        is indistinguishable from a stuck one.
        """

        from sqlalchemy import func, select

        metadata = self.harvest_metadata(ctx.schema)
        records = metadata.tables[f"{ctx.schema}.{RECORDS_TABLE}"]
        identifiers = metadata.tables[f"{ctx.schema}.{IDENTIFIERS_TABLE}"]

        async with (
            httpx.AsyncClient(timeout=DUMP_TIMEOUT, follow_redirects=True) as client,
            client.stream("GET", self.config.dump_url, headers=_DUMP_REQUEST_HEADERS) as response,
        ):
            response.raise_for_status()
            edition = _dump_edition(response.headers)
            declared = response.headers.get("content-length")
            declared_encoding = response.headers.get("content-encoding")
            total = int(declared) if declared and declared.isdigit() else None

            if edition is not None and edition == ctx.watermark:
                kept = ctx.connection.execute(
                    select(func.count()).select_from(records)
                ).scalar_one()
                if kept:
                    ctx.progress(total or 0, total or 0)
                    logger.info("Dump %s is unchanged; keeping %s records", edition, kept)
                    return HarvestResult(
                        watermark=edition, records=int(kept), total_records=int(kept)
                    )

            self._reset_tables(ctx.connection, records, identifiers)
            dropped = self._drop_indexes(ctx.connection, metadata)

            stream = _DumpStream()
            parser = etree.XMLPullParser(events=("end",))
            checked_format = False
            read = 0
            pending: list[_ParsedRecord] = []

            async for chunk in response.aiter_bytes(DOWNLOAD_CHUNK_SIZE):
                read += len(chunk)
                document = stream.feed(chunk)
                if document and not checked_format:
                    _reject_unreadable_dump(document)
                    checked_format = True
                if total is not None and stream.inflating is False and declared_encoding:
                    # A transport inflated the body despite the identity request,
                    # so Content-Length counts the compressed download and not
                    # the stream being read. Better no percentage than a wrong one.
                    total = None
                # A compressed chunk inflates to many times its size, and libxml2
                # rejects a push buffer that large ("Buffer size limit exceeded").
                # Feed it in bounded slices, draining after each so neither the
                # parser's buffer nor the pending batch grows with the ratio.
                for offset in range(0, len(document), PARSE_FEED_SIZE):
                    parser.feed(document[offset : offset + PARSE_FEED_SIZE])
                    for parsed in self._drain(parser):
                        pending.append(parsed)
                        if len(pending) >= HARVEST_BATCH_SIZE:
                            self._write_batch(ctx.connection, records, identifiers, pending)
                            pending.clear()
                ctx.progress(read, total)
                # The parse and the writes are synchronous and long. Yield so
                # this hour-long coroutine does not monopolize the loop.
                await asyncio.sleep(0)

            # A truncated download leaves the document unclosed; failing here is
            # what keeps a partial catalogue from being published as a whole one.
            parser.close()
            pending.extend(self._drain(parser))
            if pending:
                self._write_batch(ctx.connection, records, identifiers, pending)

            for index in dropped:
                index.create(ctx.connection)

            # Counted rather than accumulated: the dump repeats a system number
            # occasionally, and the figure an operator reads should be the size
            # of the copy, not the number of records walked.
            harvested = ctx.connection.execute(
                select(func.count()).select_from(records)
            ).scalar_one()

        ctx.progress(read, read)
        # A run replaces the whole copy, so its work and the copy's size are
        # the same figure; both are reported so the operator's two questions
        # are answered from the same place as for an incremental plugin.
        return HarvestResult(
            watermark=edition, records=int(harvested), total_records=int(harvested)
        )

    def _drain(self, parser: etree.XMLPullParser) -> Iterator[_ParsedRecord]:
        for _, element in parser.read_events():
            if etree.QName(element).localname != "record":
                continue
            parsed = _parse_dump_record(element, self._system_number)
            _release(element)
            if parsed is not None:
                yield parsed

    @staticmethod
    def _reset_tables(connection: Connection, records: Table, identifiers: Table) -> None:
        """Empty the previous snapshot; TRUNCATE rolls back with the harvest."""

        from sqlalchemy import text

        preparer = connection.dialect.identifier_preparer
        names = ", ".join(preparer.format_table(table) for table in (identifiers, records))
        connection.execute(text(f"TRUNCATE {names}"))

    @staticmethod
    def _drop_indexes(connection: Connection, metadata: MetaData) -> list[Index]:
        """Drop lookup indexes for the bulk load and report them for recreation.

        Maintaining them row by row across ten million inserts costs far more
        than building them once at the end.
        """

        dropped: list[Index] = []
        for table in metadata.tables.values():
            for index in sorted(table.indexes, key=lambda index: index.name or ""):
                index.drop(connection)
                dropped.append(index)
        return dropped

    @staticmethod
    def _write_batch(
        connection: Connection,
        records: Table,
        identifiers: Table,
        batch: list[_ParsedRecord],
    ) -> None:
        """Insert one batch, tolerating records the dump repeats.

        A single duplicated system number would otherwise abort an hours-long
        harvest at whatever point it appeared.
        """

        from sqlalchemy.dialects.postgresql import insert

        record_rows = {
            parsed.sysno: {
                "sysno": parsed.sysno,
                "title_key": parsed.title_key,
                "author_key": parsed.author_key,
                "year": parsed.year,
                "marc": parsed.marc,
            }
            for parsed in batch
        }
        identifier_rows = {
            (parsed.sysno, kind.value, value): {
                "sysno": parsed.sysno,
                "kind": kind.value,
                "value": value,
            }
            for parsed in batch
            for kind, value in parsed.identifiers
        }

        connection.execute(
            insert(records).on_conflict_do_nothing(index_elements=["sysno"]),
            list(record_rows.values()),
        )
        if identifier_rows:
            connection.execute(
                insert(identifiers).on_conflict_do_nothing(
                    index_elements=["sysno", "kind", "value"]
                ),
                list(identifier_rows.values()),
            )

    async def prefetch(self, requests: Sequence[LinkRequest]) -> None:
        """Retrieve the whole window's candidates in three queries.

        Asked one record at a time, retrieval is three round trips per record
        against a table of millions — and the round trips, not the scans, are
        the cost: two hundred identifier lookups measured 1.77 s where the same
        identifiers asked for together measured 14 ms. The queries here are the
        same ones, widened to the window and attributed back by the identifier
        or title that matched.
        """

        self._rows_cache = {}
        if not requests or self.harvest_storage is None:
            return
        await asyncio.to_thread(self._load_window, requests)

    def _load_window(self, requests: Sequence[LinkRequest]) -> None:
        from sqlalchemy import and_, or_, select

        storage = self.harvest_storage
        if storage is None:
            return
        metadata = self.harvest_metadata(storage.schema)
        records = metadata.tables[f"{storage.schema}.{RECORDS_TABLE}"]
        identifiers = metadata.tables[f"{storage.schema}.{IDENTIFIERS_TABLE}"]

        wanted = {
            (request.base, request.system_number): _record_identifiers(request.record)
            for request in requests
        }
        by_kind: defaultdict[str, set[str]] = defaultdict(set)
        for found in wanted.values():
            for kind, values in found.items():
                by_kind[kind.value].update(values)

        chosen: dict[tuple[str, str], list[str]] = {}
        #: Which path filled each key. The identifier pass claims a key before
        #: the title pass is offered what is left, so this is written once.
        routes: dict[tuple[str, str], MatchRoute] = {}

        with storage.connection() as connection:
            # The value comes back alongside the sysno because it is what
            # attributes a row to the record that asked for it; a single-record
            # query can leave it out, a windowed one cannot.
            hits: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
            clauses = [
                and_(identifiers.c.kind == kind, identifiers.c.value.in_(sorted(values)))
                for kind, values in by_kind.items()
                if values
            ]
            if clauses:
                rows = connection.execute(
                    select(identifiers.c.sysno, identifiers.c.kind, identifiers.c.value).where(
                        or_(*clauses)
                    )
                ).mappings()
                for row in rows:
                    hits[(row["kind"], row["value"])].append(row["sysno"])

            for key, found in wanted.items():
                # One record can match on several identifiers; rank it by its
                # strongest, exactly as the per-record query does.
                best: dict[str, int] = {}
                for kind, values in found.items():
                    priority = _IDENTIFIER_PRIORITY.get(kind, len(DumpIdentifier))
                    for value in values:
                        for sysno in hits.get((kind.value, value), ()):
                            if priority < best.get(sysno, len(DumpIdentifier)):
                                best[sysno] = priority
                ranked = sorted(best.items(), key=lambda item: (item[1], item[0]))
                if ranked:
                    chosen[key] = [sysno for sysno, _ in ranked[: self.config.candidate_limit]]
                    routes[key] = MatchRoute.Identifier

            self._load_window_titles(connection, records, requests, chosen, routes)

            # One read of the MARC for every survivor of both paths. Ranking
            # first and reading blobs second is what keeps a placeholder ISBN
            # shared by thousands of records from pulling thousands of blobs.
            needed = sorted({sysno for sysnos in chosen.values() for sysno in sysnos})
            marc_by_sysno: dict[str, bytes] = {}
            if needed:
                marc_by_sysno = dict(
                    connection.execute(
                        select(records.c.sysno, records.c.marc).where(records.c.sysno.in_(needed))
                    ).all()
                )

        for key in wanted:
            self._rows_cache[key] = (
                routes.get(key),
                [
                    {"sysno": sysno, "marc": marc_by_sysno[sysno]}
                    for sysno in chosen.get(key, ())
                    if sysno in marc_by_sysno
                ],
            )

    def _load_window_titles(
        self,
        connection: Connection,
        records: Table,
        requests: Sequence[LinkRequest],
        chosen: dict[tuple[str, str], list[str]],
        routes: dict[tuple[str, str], MatchRoute],
    ) -> None:
        """Fill in the records no identifier matched, from their titles.

        Ranking moves to Python because each record prefers its own year and
        author, which one query cannot order by. Only the small columns are
        read here; the MARC is fetched once for the survivors of both paths.
        """

        from sqlalchemy import select

        probes = {}
        for request in requests:
            key = (request.base, request.system_number)
            if key in chosen:
                continue
            title_key, year, author_key = _title_probe(request.record)
            if title_key:
                probes[key] = (title_key, year, author_key)
        if not probes:
            return

        by_title: defaultdict[str, list[Any]] = defaultdict(list)
        rows = connection.execute(
            select(
                records.c.sysno, records.c.title_key, records.c.year, records.c.author_key
            ).where(records.c.title_key.in_(sorted({probe[0] for probe in probes.values()})))
        ).mappings()
        for row in rows:
            by_title[row["title_key"]].append(row)

        for key, (title_key, year, author_key) in probes.items():
            ranked = sorted(
                by_title.get(title_key, ()),
                key=lambda row: (
                    0 if year is not None and row["year"] == year else 1,
                    0 if author_key and row["author_key"] == author_key else 1,
                    row["sysno"],
                ),
            )
            if ranked:
                chosen[key] = [row["sysno"] for row in ranked[: self.config.candidate_limit]]
                routes[key] = MatchRoute.Title

    def _candidates(self, record: MarcRecord, key: tuple[str, str] | None = None) -> _Retrieval:
        """Retrieve comparable records: identifiers first, title as a fallback.

        The path taken comes back with the candidates because it is what the
        caller's floor is chosen by, and it cannot be recovered afterwards from
        the rows themselves.
        """

        cached = self._rows_cache.get(key) if key is not None else None
        if cached is not None:
            route, rows = cached
        else:
            storage = self.harvest_storage
            if storage is None:
                raise HarvestStorageUnavailable("Local dump data is no longer bound")

            metadata = self.harvest_metadata(storage.schema)
            records = metadata.tables[f"{storage.schema}.{RECORDS_TABLE}"]
            identifiers = metadata.tables[f"{storage.schema}.{IDENTIFIERS_TABLE}"]

            with storage.connection() as connection:
                rows = self._rows_by_identifier(connection, records, identifiers, record)
                route = MatchRoute.Identifier if rows else None
                if not rows:
                    rows = self._rows_by_title(connection, records, record)
                    route = MatchRoute.Title if rows else None

        candidates: list[_Candidate] = []
        for row in rows:
            try:
                element = etree.fromstring(zlib.decompress(row["marc"]))
                candidates.append(_Candidate(row["sysno"], MarcRecord.from_xml(element)))
            except Exception:
                # One unparseable union-catalogue record must not fail the record
                # being linked; the remaining candidates are still comparable.
                logger.warning("Skipping unparseable dump record %s", row["sysno"], exc_info=True)
        return _Retrieval(route, candidates)

    def _rows_by_identifier(
        self,
        connection: Connection,
        records: Table,
        identifiers: Table,
        record: MarcRecord,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import and_, or_, select

        wanted = _record_identifiers(record)
        clauses = [
            and_(identifiers.c.kind == kind.value, identifiers.c.value.in_(sorted(values)))
            for kind, values in wanted.items()
            if values
        ]
        if not clauses:
            return []

        # Rank on identifiers alone and read MARC only for the survivors. A
        # placeholder ISBN shared by thousands of records would otherwise pull
        # thousands of blobs into memory to discard all but a handful.
        found = connection.execute(
            select(identifiers.c.sysno, identifiers.c.kind).where(or_(*clauses))
        ).mappings()

        # One record can match on several identifiers; rank it by its strongest.
        best: dict[str, int] = {}
        for row in found:
            priority = _IDENTIFIER_PRIORITY.get(DumpIdentifier(row["kind"]), len(DumpIdentifier))
            if priority < best.get(row["sysno"], len(DumpIdentifier)):
                best[row["sysno"]] = priority

        ranked = sorted(best.items(), key=lambda item: (item[1], item[0]))
        sysnos = [sysno for sysno, _ in ranked[: self.config.candidate_limit]]
        if not sysnos:
            return []

        marc_by_sysno = dict(
            connection.execute(
                select(records.c.sysno, records.c.marc).where(records.c.sysno.in_(sysnos))
            ).all()
        )
        return [
            {"sysno": sysno, "marc": marc_by_sysno[sysno]}
            for sysno in sysnos
            if sysno in marc_by_sysno
        ]

    def _rows_by_title(
        self, connection: Connection, records: Table, record: MarcRecord
    ) -> list[dict[str, Any]]:
        """Fall back to an identical normalized title.

        Generic titles match many records, so year and author agreement only
        order the candidates — narrowing on them would lose the right record
        whenever the two catalogues disagree about either.
        """

        from sqlalchemy import case, select

        title_key, year, author_key = _title_probe(record)
        if not title_key:
            return []

        preferences = []
        if year is not None:
            preferences.append(case((records.c.year == year, 0), else_=1))
        if author_key:
            preferences.append(case((records.c.author_key == author_key, 0), else_=1))

        rows = connection.execute(
            select(records.c.sysno, records.c.marc)
            .where(records.c.title_key == title_key)
            .order_by(*preferences, records.c.sysno)
            .limit(self.config.candidate_limit)
        ).mappings()
        return [dict(row) for row in rows]

    async def run(
        self,
        base: str,
        system_number: str,
        record: MarcRecord,
        target_base: str,
    ) -> AuthorityLink | None:
        if target_base != self.config.target_base:
            raise ValueError(f"Unsupported target base: {target_base}")
        if self.harvest_storage is None:
            # Reporting "no link" here would be read as "no match exists", and
            # the caller deletes links that are no longer found.
            raise HarvestStorageUnavailable(
                f"Linking against {self.config.target_base} needs a harvested copy of the "
                "union catalogue; run the 'skc' harvest first"
            )

        retrieval = await asyncio.to_thread(self._candidates, record, (base, system_number))
        if not retrieval.candidates:
            return None

        best: _Candidate | None = None
        best_comparison: RecordComparisonResult | None = None
        best_score = 0.0
        for candidate in retrieval.candidates:
            comparison = await self._comparator.run(record, candidate.record)
            if best is None or comparison.overall_score > best_score:
                best, best_comparison, best_score = candidate, comparison, comparison.overall_score

        if best is None or best_score < self._minimum_confidence_for(retrieval.route):
            return None

        return AuthorityLink(
            base=target_base,
            system_number=best.sysno,
            record=best.record,
            confidence=best_score,
            # The pair chosen here is the pair the pipeline compares next.
            comparison=best_comparison,
            matched_by=retrieval.route,
        )

    def _minimum_confidence_for(self, route: MatchRoute | None) -> float:
        """The floor this candidate has to clear, given how it was found.

        An unknown route is treated as the title one: the floors only differ
        because the identifier path brings evidence with it, so anything that
        cannot show which path it took does not get the benefit of that.
        """

        if route is MatchRoute.Identifier:
            return self.config.identifier_minimum_confidence
        return self.config.title_minimum_confidence

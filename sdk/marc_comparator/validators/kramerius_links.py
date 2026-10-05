import asyncio
import hashlib
import json
import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from kramerius import KrameriusClient, KrameriusConfig, KrameriusField, Model
from kramerius.schemas import KrameriusDocument
from marcdantic import MarcRecord
from marcdantic.fields import VariableField
from marcdantic.selectors import IsbnActiveJq, IssnActiveJq, NbnActiveJq
from pydantic import BaseModel
from solrify import F, G

from ..harvest import HarvestContext, HarvestResult, HarvestStorageUnavailable
from ..reports import ReportFile
from ._base import (
    BaseValidator,
    ReportInput,
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)


class KrameriusLinksValidatorConfig(BaseModel):
    url_to_pid_pattern: str = (
        r"https?://(?:www\.)?digitalniknihovna\.cz/mzk/uuid/(?P<pid>uuid:[0-9a-fA-F-]+)(?:\?.*)?"
    )
    url_to_pid_wrong_path_pattern: str = (
        r"https?://(?:www\.)?digitalniknihovna\.cz/mzk/[^/]+/(?P<pid>uuid:[0-9a-fA-F-]+)(?:\?.*)?"
    )
    url_to_pid_fallback_pattern: str = r"https?://[^/]+/.*?(?P<pid>uuid:[0-9a-fA-F-]+)(?:\?.*)?"
    link_text_pattern: str = r"Digitalizovaný dokument"

    #: Which hosts are this library's own digital library, including any legacy
    #: address still in circulation.
    #:
    #: A record may legitimately link to another institution's Kramerius — the
    #: same document is often held by several — and such a link is not ours to
    #: correct. Only a URL on one of these hosts is judged against our expected
    #: format or looked up in our index; anything else is reported as an
    #: observation and left alone.
    own_host_pattern: str = r"^https?://(?:www\.)?(?:digitalniknihovna\.cz/mzk|kramerius\.mzk\.cz)"

    kramerius_host: str = "https://api.kramerius.mzk.cz/search"
    kramerius_client_url: str = "https://www.digitalniknihovna.cz/mzk/uuid/{pid}"
    solr_cloud: bool = True
    search_page_size: int = 10

    #: Seconds to wait for one Solr response.
    #:
    #: The client library defaults to 30, which is tuned for the per-record
    #: lookups the validator makes. A harvest page asks for a thousand documents
    #: at once, and on a loaded Kramerius that does not come back inside half a
    #: minute: every page times out, the retries exhaust, and an hours-long
    #: harvest dies on its first request having reported no progress at all.
    search_timeout: int = 180

    #: An identifier should resolve to one document. When it resolves to more, the
    #: extra matches are almost always wrong metadata in Kramerius — MZK's index has
    #: ČNB numbers shared by dozens to hundreds of unrelated documents. Those hits are
    #: not turned into links; they are reported for review instead.
    max_documents_per_identifier: int = 1


VALIDATION_FIELD = ValidationTarget(tag="856", codes=["u", "y"])

TARGET_MODELS = [
    Model.Monograph,
    Model.MonographUnit,
    Model.Periodical,
    Model.PeriodicalVolume,
    Model.PeriodicalItem,
    Model.Supplement,
    Model.Graphic,
    Model.Map,
    Model.Sheetmusic,
    Model.SoundRecording,
    Model.Archive,
    Model.Manuscript,
]
VALID_TOP_LEVEL_MODELS = {
    Model.Monograph,
    Model.Periodical,
    Model.Graphic,
    Model.Map,
    Model.Sheetmusic,
    Model.SoundRecording,
    Model.Archive,
    Model.Manuscript,
}
FL = [
    f.value
    for f in [
        KrameriusField.OwnPidPath,
        KrameriusField.ModelPath,
        KrameriusField.Level,
        # Returned so each hit can be attributed back to the identifier that matched
        # it, which is what lets an unreliable identifier be dropped on its own.
        KrameriusField.Barcode,
        KrameriusField.Isbn,
        KrameriusField.Issn,
        KrameriusField.Nbn,
    ]
]
HARVEST_FL = [
    "compositeId",
    KrameriusField.Pid.value,
    KrameriusField.Model.value,
    *FL,
    "indexed",
]
MAX_QUERY_PARTS = 50
HARVEST_PAGE_SIZE = 1000

DOCUMENTS_TABLE = "documents"
IDENTIFIERS_TABLE = "identifiers"
INDEXED_FIELD = "indexed"
TARGET_MODEL_VALUES = frozenset(model.value for model in TARGET_MODELS)

#: The KrameriusDocument attribute carrying each identifier we search on.
IDENTIFIER_DOC_ATTR = {
    KrameriusField.Barcode: "barcode",
    KrameriusField.Isbn: "isbn",
    KrameriusField.Issn: "issn",
    KrameriusField.Nbn: "nbn",
}

#: How many candidate PIDs to name in a review result. The identifier is reported
#: alongside them, so the full set stays one Solr query away.
PIDS_IN_REVIEW_SAMPLE = 10

logger = logging.getLogger(__name__)

#: Standard 856 $y link text written for added/replaced links.
STANDARD_LINK_TEXT = "Digitalizovaný dokument"


def _solr_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _harvest_query(watermark: str | None, upper: str) -> str:
    timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
    if watermark is not None and not timestamp_pattern.fullmatch(watermark):
        raise ValueError(f"Invalid Kramerius harvest watermark: {watermark!r}")
    if not timestamp_pattern.fullmatch(upper):
        raise ValueError(f"Invalid Kramerius harvest upper bound: {upper!r}")
    lower = watermark or "*"
    # Solr date ranges accept their ISO-8601 endpoints directly; square brackets
    # make both sides inclusive, which deliberately overlaps the prior watermark.
    indexed_range = f"{INDEXED_FIELD}:[{lower} TO {upper}]"
    if watermark is not None:
        # Do not filter incremental pages by model: an object that changed from a
        # stored model to page (or any excluded model) must remove its old row.
        return indexed_range
    # solrify's `F` takes a list of values to mean "any of these" and builds
    # the OR itself; its `ValueType` alias lists only the scalars.
    return (
        f"{indexed_range} AND "
        f"{F(KrameriusField.Model, TARGET_MODELS)}"  # pyright: ignore[reportArgumentType]
    )


def _required_scalar(document: dict[str, Any], field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Kramerius document has no usable {field!r}: {value!r}")
    return value


def _string_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value if isinstance(item, str)]


def _load_local_documents(connection, documents, identifiers, rows) -> list[KrameriusDocument]:
    from sqlalchemy import select

    if not rows:
        return []
    values_by_document: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    composite_ids = [row["composite_id"] for row in rows]
    for row in connection.execute(
        select(identifiers.c.composite_id, identifiers.c.kind, identifiers.c.value).where(
            identifiers.c.composite_id.in_(composite_ids)
        )
    ).mappings():
        values_by_document[row["composite_id"]][row["kind"]].append(row["value"])

    result: list[KrameriusDocument] = []
    for row in rows:
        data: dict[str, Any] = {
            "pid": row["pid"],
            "own_pid_path": row["own_pid_path"],
            "model": row["model"],
            "own_model_path": row["model_path"],
            "level": row["level"],
        }
        for field in IDENTIFIER_DOC_ATTR:
            data[field.value] = values_by_document[row["composite_id"]].get(field.value, [])
        result.append(KrameriusDocument.model_validate(data))
    return result


#: Asked together, in this order, so the record is handed to jq once.
#:
#: Handing it over converts the whole record into jq's own values, so the
#: cost follows the size of the record rather than what the filter selects:
#: three selectors asked separately measured 0.675 ms against 0.231 ms asked
#: together, which is what one of them costs alone.
_IDENTIFIER_SELECTORS = (
    (KrameriusField.Isbn, IsbnActiveJq),
    (KrameriusField.Issn, IssnActiveJq),
    (KrameriusField.Nbn, NbnActiveJq),
)


#: The 856 fields, asked for alongside the identifiers rather than on their own.
_ELOCATION_FIELDS_JQ = '.["856"][]?'

#: Every filter this validator asks of a record, in one list, so the record is
#: handed to jq once.
_ALL_FILTERS = [jq_filter for _field, jq_filter in _IDENTIFIER_SELECTORS] + [_ELOCATION_FIELDS_JQ]


@dataclass(frozen=True)
class _RecordQueries:
    """Everything this validator asks jq about one record.

    Asked together because handing a record to jq converts the whole of it
    into jq's own values, so the cost follows the size of the record and not
    what the filter selects. Four filters asked separately convert the same
    record four times.
    """

    identifiers: list[tuple[KrameriusField, str]]
    elocation_fields: list[VariableField]


def _query_record(record: MarcRecord) -> _RecordQueries:
    """Ask every filter at once and sort the answers out afterwards."""

    *identifier_values, elocation = record.variable_fields.query_many(_ALL_FILTERS)

    raw_fields = [
        (
            KrameriusField.Barcode,
            [i.barcode for i in record.issues_selector.all if i.barcode],
        ),
        *(
            (field, values)
            for (field, _), values in zip(_IDENTIFIER_SELECTORS, identifier_values, strict=True)
        ),
    ]
    return _RecordQueries(
        identifiers=[(field, value) for field, values in raw_fields for value in (values or [])],
        # query_fields would have validated these; query_many hands back the
        # plain dicts jq produced, so they are validated here instead.
        elocation_fields=[VariableField.model_validate(field) for field in elocation],
    )


def _window_key(searched_values: dict[KrameriusField, set[str]]) -> frozenset[tuple[str, str]]:
    """What a record is asking about, as something that can key a cache.

    A record asks the same question every time, so the values it searches by
    identify its answer within a window without the host having to name it.
    """

    return frozenset(
        (field.value, value) for field, values in searched_values.items() for value in values
    )


@dataclass
class FoundKrameriusLink:
    pid: str
    model: Model
    has_wrong_model: bool = False
    level: int = 0
    #: The top of this document's own hierarchy, when the link landed below it.
    #: Carrying it is what lets the result name the PID the link should use, and
    #: what makes the finding repairable instead of merely reported.
    top_level_pid: str | None = None


@dataclass
class AmbiguousIdentifier:
    """
    An identifier that resolved to more Kramerius documents than a record can have.

    Its hits are withheld rather than proposed as links: one identifier pointing at
    several unrelated documents is a metadata error on the Kramerius side, and which
    (if any) of them belongs to the record is a judgement call for a curator.
    """

    #: None when the hits matched no searched value verbatim.
    field: KrameriusField | None
    values: list[str]
    pids: list[str]


class KrameriusLinksValidator(BaseValidator):
    """
    Validator to check for the presence of Kramerius links in MARC records.
    """

    config_model = KrameriusLinksValidatorConfig
    can_generate_report = True
    needs_harvest = True
    harvest_schema_version = 1

    def __init__(self, config: KrameriusLinksValidatorConfig):
        self.config = config

        self.url_to_pid_regex = re.compile(config.url_to_pid_pattern)
        self.url_to_pid_wrong_path_regex = re.compile(config.url_to_pid_wrong_path_pattern)
        self.url_to_pid_fallback_regex = re.compile(config.url_to_pid_fallback_pattern)
        self.link_text_regex = re.compile(config.link_text_pattern)
        self.own_host_regex = re.compile(config.own_host_pattern)

        self.client = KrameriusClient(
            # KrameriusConfig gives max_retries, retry_timeout and
            # max_active_processes defaults at runtime; its signature does not.
            KrameriusConfig(  # pyright: ignore[reportCallIssue]
                host=config.kramerius_host,
                solr_cloud=config.solr_cloud,
                search_page_size=config.search_page_size,
                timeout=config.search_timeout,
            )
        )

        #: Documents for the window the host last announced, keyed by what each
        #: record searches on. Replaced wholesale by each prefetch, so it holds
        #: one window and not a run.
        self._documents_cache: dict[frozenset[tuple[str, str]], list[KrameriusDocument]] = {}
        #: What each record in the current window asks jq, keyed by identity.
        #: Populated only while `_window_records` holds those records alive, so
        #: an id cannot be reused underneath an entry.
        self._record_queries: dict[int, _RecordQueries] = {}
        self._window_records: Sequence[MarcRecord] = ()

    def harvest_source_identity(self) -> str:
        """Fingerprint only settings that change the Solr dataset being copied."""

        source = json.dumps(
            {
                "host": str(self.config.kramerius_host).rstrip("/"),
                "solr_cloud": self.config.solr_cloud,
                "search_endpoint": "api/client/v7.0/search",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(source.encode()).hexdigest()

    @classmethod
    def harvest_metadata(cls, schema: str):
        """Declare the plugin-owned lookup tables.

        SQLAlchemy stays an optional dependency for ordinary SDK and CLI use: it is
        imported only when the host asks for storage metadata or binds storage.
        """

        from sqlalchemy import (
            Column,
            ForeignKey,
            Index,
            Integer,
            MetaData,
            String,
            Table,
            Text,
        )

        metadata = MetaData(schema=schema)
        documents = Table(
            DOCUMENTS_TABLE,
            metadata,
            Column("composite_id", Text, primary_key=True),
            Column("pid", Text, nullable=False),
            Column("root_pid", Text, nullable=False),
            Column("own_pid_path", Text, nullable=False),
            Column("root_model", String(32), nullable=False),
            Column("model", String(32), nullable=False),
            Column("model_path", Text, nullable=False),
            Column("level", Integer, nullable=False),
            Column("indexed", String(32), nullable=False),
        )
        Index("ix_kramerius_documents_pid", documents.c.pid)

        identifiers = Table(
            IDENTIFIERS_TABLE,
            metadata,
            Column(
                "composite_id",
                Text,
                ForeignKey(f"{schema}.{DOCUMENTS_TABLE}.composite_id", ondelete="CASCADE"),
                primary_key=True,
            ),
            Column("kind", String(16), primary_key=True),
            Column("value", Text, primary_key=True),
        )
        Index(
            "ix_kramerius_identifiers_kind_value",
            identifiers.c.kind,
            identifiers.c.value,
        )
        return metadata

    async def harvest(self, ctx: HarvestContext) -> HarvestResult:
        """Stream one bounded Solr snapshot into the host-owned transaction."""

        upper = _solr_timestamp(datetime.now(UTC))
        query = _harvest_query(ctx.watermark, upper)
        processed = 0

        async for documents, total in self._solr_cursor_pages(query):
            stored = [doc for doc in documents if doc.get("model") in TARGET_MODEL_VALUES]
            self._replace_harvest_page(
                ctx.connection,
                ctx.schema,
                documents,
                stored,
            )
            processed += len(documents)
            ctx.progress(processed, total)

        # An empty successful run is meaningful and advances the bounded watermark.
        if processed == 0:
            ctx.progress(0, 0)

        # `processed` counts one incremental window, which after the first run is
        # a small fraction of the copy. Count what the copy actually holds so an
        # operator can tell a day's changes from the dataset behind them.
        from sqlalchemy import func, select

        documents = self.harvest_metadata(ctx.schema).tables[f"{ctx.schema}.{DOCUMENTS_TABLE}"]
        held = ctx.connection.execute(select(func.count()).select_from(documents)).scalar_one()
        return HarvestResult(watermark=upper, records=processed, total_records=int(held))

    async def _solr_cursor_pages(self, query: str):
        """Yield raw pages because KrameriusDocument drops cursor/update fields."""

        search = self.client.Search
        cursor = "*"
        seen_cursors = {cursor}
        estimated_total = 0
        received = 0
        while True:
            response = await asyncio.to_thread(
                search._session.get,
                f"{search._config.host}/{search._config.endpoint}",
                params={
                    "q": query,
                    "rows": HARVEST_PAGE_SIZE,
                    "fl": HARVEST_FL,
                    "sort": "compositeId asc",
                    "cursorMark": cursor,
                },
                timeout=search._timeout,
            )
            response.raise_for_status()
            payload = response.json()
            header = payload.get("responseHeader", {})
            if header.get("partialResults") in {True, "true"}:
                raise RuntimeError("Kramerius Solr returned partial cursor results")
            result = payload["response"]
            documents = result["docs"]
            next_cursor = payload.get("nextCursorMark")
            if not isinstance(documents, list):
                raise RuntimeError("Kramerius Solr cursor response has invalid documents")
            if not isinstance(next_cursor, str) or not next_cursor:
                raise RuntimeError("Kramerius Solr cursor response has invalid nextCursorMark")
            # numFound is an estimate here, not a contract. Kramerius keeps
            # indexing while a walk of this size is in flight, so the count
            # drifts even for a bounded `indexed` range, and a harvest must not
            # fail because of that. cursorMark is what guarantees a complete,
            # duplicate-free walk; the count only drives the progress bar, so
            # keep it monotonic and never below what has already been read.
            received += len(documents)
            estimated_total = max(estimated_total, int(result["numFound"]), received)

            if documents:
                yield documents, estimated_total
            if next_cursor == cursor:
                break
            if next_cursor in seen_cursors:
                raise RuntimeError("Kramerius Solr cursor entered a cycle")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    @classmethod
    def _replace_harvest_page(
        cls,
        connection,
        schema: str,
        changed_documents: list[dict[str, Any]],
        stored_documents: list[dict[str, Any]],
    ) -> None:
        """Replace changed documents and their identifiers without retaining a page."""

        from sqlalchemy import delete, insert

        metadata = cls.harvest_metadata(schema)
        documents = metadata.tables[f"{schema}.{DOCUMENTS_TABLE}"]
        identifiers = metadata.tables[f"{schema}.{IDENTIFIERS_TABLE}"]

        composite_ids = [_required_scalar(doc, "compositeId") for doc in changed_documents]
        if composite_ids:
            # FK cascade removes mappings even if the document changed out of the
            # harvested model set.
            connection.execute(delete(documents).where(documents.c.composite_id.in_(composite_ids)))

        document_rows: list[dict[str, Any]] = []
        identifier_rows: list[dict[str, str]] = []
        for raw in stored_documents:
            composite_id = _required_scalar(raw, "compositeId")
            pid = _required_scalar(raw, KrameriusField.Pid.value)
            model = _required_scalar(raw, KrameriusField.Model.value)
            own_pid_path = _required_scalar(raw, KrameriusField.OwnPidPath.value)
            model_path = _required_scalar(raw, KrameriusField.ModelPath.value)
            indexed = _required_scalar(raw, INDEXED_FIELD)
            level = int(raw.get(KrameriusField.Level.value) or 0)
            document_rows.append(
                {
                    "composite_id": composite_id,
                    "pid": pid,
                    "root_pid": own_pid_path.split("/")[0],
                    "own_pid_path": own_pid_path,
                    "root_model": model_path.split("/")[0],
                    "model": model,
                    "model_path": model_path,
                    "level": level,
                    "indexed": indexed,
                }
            )
            for field in IDENTIFIER_DOC_ATTR:
                for value in _string_values(raw.get(field.value)):
                    identifier_rows.append(
                        {
                            "composite_id": composite_id,
                            "kind": field.value,
                            "value": value,
                        }
                    )

        if document_rows:
            connection.execute(insert(documents), document_rows)
        if identifier_rows:
            # Duplicate values within one Solr array are irrelevant to lookup and
            # would violate the normalized table's primary key.
            unique_rows = list(
                {
                    (row["composite_id"], row["kind"], row["value"]): row for row in identifier_rows
                }.values()
            )
            connection.execute(insert(identifiers), unique_rows)

    async def prefetch(self, records: Sequence[MarcRecord]) -> None:
        """Look the whole window up in one query rather than one per record.

        Every record asks the same shape of question of the same two tables,
        and asked one at a time that query was the single largest cost in a
        pass — the round trip, not the scan. Answering the window together
        leaves each record reading its own documents out of memory.
        """

        self._documents_cache = {}
        self._record_queries = {}
        self._window_records = ()
        if not records or not self.harvest_ready:
            return
        try:
            await asyncio.to_thread(self._load_window, records)
        except HarvestStorageUnavailable:
            # Nothing is warmed and every record falls back to its own lookup,
            # which is what would have happened without a window at all.
            logger.info("Harvested Kramerius data became unavailable while prefetching")

    def _load_window(self, records: Sequence[MarcRecord]) -> None:
        # Held for as long as the answers below are keyed by their identity.
        self._window_records = records

        wanted: list[tuple[frozenset[tuple[str, str]], dict[KrameriusField, set[str]]]] = []
        combined: dict[KrameriusField, set[str]] = defaultdict(set)
        for record in records:
            queries = _query_record(record)
            self._record_queries[id(record)] = queries

            searched: dict[KrameriusField, set[str]] = defaultdict(set)
            for field, value in queries.identifiers:
                searched[field].add(value)
            wanted.append((_window_key(searched), searched))
            for field, values in searched.items():
                combined[field].update(values)

        found = self._query_documents_by_identifiers(combined)

        # A document answers a record when it carries one of the values that
        # record searched on — the same test the caller applies to attribute a
        # hit to an identifier. Kept in query order so a window returns what a
        # single lookup would have returned, in the order it would have.
        by_value: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
        for position, document in enumerate(found):
            for field, attr in IDENTIFIER_DOC_ATTR.items():
                for value in getattr(document, attr) or []:
                    by_value[(field.value, value)].append(position)

        for key, _searched in wanted:
            positions = {position for pair in key for position in by_value.get(pair, ())}
            self._documents_cache[key] = [found[position] for position in sorted(positions)]

    def _queries_for(self, record: MarcRecord) -> _RecordQueries:
        """What this record asks jq, from the window if it was prefetched.

        Only `_load_window` ever fills the cache, and only while
        `_window_records` keeps those records alive: caching a record from
        anywhere else would leave an entry keyed by an id that a later object
        could be handed once this one is collected.
        """

        cached = self._record_queries.get(id(record))
        return cached if cached is not None else _query_record(record)

    def _local_documents_by_identifiers(
        self, searched_values: dict[KrameriusField, set[str]]
    ) -> list[KrameriusDocument]:
        cached = self._documents_cache.get(_window_key(searched_values))
        if cached is not None:
            return cached
        return self._query_documents_by_identifiers(searched_values)

    def _query_documents_by_identifiers(
        self, searched_values: dict[KrameriusField, set[str]]
    ) -> list[KrameriusDocument]:
        from sqlalchemy import and_, or_, select

        storage = self.harvest_storage
        if storage is None:
            return []
        metadata = self.harvest_metadata(storage.schema)
        documents = metadata.tables[f"{storage.schema}.{DOCUMENTS_TABLE}"]
        identifiers = metadata.tables[f"{storage.schema}.{IDENTIFIERS_TABLE}"]
        clauses = [
            and_(identifiers.c.kind == field.value, identifiers.c.value.in_(values))
            for field, values in searched_values.items()
            if values
        ]
        if not clauses:
            return []

        with storage.connection() as connection:
            rows = connection.execute(
                select(documents)
                .join(identifiers, identifiers.c.composite_id == documents.c.composite_id)
                .where(or_(*clauses))
                .distinct()
            ).mappings()
            return _load_local_documents(connection, documents, identifiers, list(rows))

    def _local_documents_by_pid(self, pid: str) -> list[KrameriusDocument]:
        from sqlalchemy import select

        storage = self.harvest_storage
        if storage is None:
            return []
        metadata = self.harvest_metadata(storage.schema)
        documents = metadata.tables[f"{storage.schema}.{DOCUMENTS_TABLE}"]
        identifiers = metadata.tables[f"{storage.schema}.{IDENTIFIERS_TABLE}"]
        with storage.connection() as connection:
            rows = connection.execute(select(documents).where(documents.c.pid == pid)).mappings()
            return _load_local_documents(connection, documents, identifiers, list(rows))

    def _remote_documents(self, query) -> list[KrameriusDocument]:
        return list(self.client.Search.search(query, fl=FL))

    async def find_kramerius_links(
        self, record: MarcRecord, current_kramerius_pids: list[str]
    ) -> tuple[list[FoundKrameriusLink], list[AmbiguousIdentifier]]:
        links: dict[str, FoundKrameriusLink] = {}

        field_query_parts = self._queries_for(record).identifiers

        searched_values: dict[KrameriusField, set[str]] = defaultdict(set)
        for field, value in field_query_parts:
            searched_values[field].add(value)

        # Hits grouped by the identifier that produced them. None collects hits that
        # match no searched value verbatim (a normalisation difference, say) — they are
        # kept, but subject to the same plausibility cap as any single identifier.
        roots_by_identifier: dict[KrameriusField | None, dict[str, FoundKrameriusLink]] = (
            defaultdict(dict)
        )

        def collect_documents(documents: Iterable[KrameriusDocument]) -> None:
            for doc in documents:
                if not doc.own_pid_path or not doc.model_path:
                    continue
                root_pid = doc.own_pid_path.split("/")[0]
                # Both paths run root -> leaf, so the root's model is the first element.
                # Taking the last one named the leaf wrongly flags parents reached via
                # child hits as non-linkable.
                root_model = Model(doc.model_path.split("/")[0])
                has_wrong_model = root_model not in VALID_TOP_LEVEL_MODELS
                link = FoundKrameriusLink(root_pid, root_model, has_wrong_model)

                matched = [
                    field
                    for field, attr in IDENTIFIER_DOC_ATTR.items()
                    if searched_values[field] & set(getattr(doc, attr) or [])
                ]
                for field in matched or [None]:
                    roots_by_identifier[field][root_pid] = link

        use_remote = not self.harvest_ready
        if self.harvest_ready:
            try:
                local_documents = await asyncio.to_thread(
                    self._local_documents_by_identifiers, searched_values
                )
                collect_documents(local_documents)
            except HarvestStorageUnavailable:
                logger.info("Harvested Kramerius data became unavailable; using Solr")
                use_remote = True

        if use_remote:
            for i in range(0, len(field_query_parts), MAX_QUERY_PARTS):
                upper = min(i + MAX_QUERY_PARTS, len(field_query_parts))
                field_query_parts_chunk = field_query_parts[i:upper]

                query = None

                for field, values in field_query_parts_chunk:
                    if query is None:
                        query = F(field, values)
                        continue

                    query |= F(field, values)

                if query is None:
                    break

                # As above for the value list; `G(...) & F(...)` is solrify's
                # own composition and comes back wider than the parameter.
                query = G(query) & F(  # pyright: ignore[reportArgumentType]
                    KrameriusField.Model,
                    TARGET_MODELS,  # pyright: ignore[reportArgumentType]
                )
                collect_documents(await asyncio.to_thread(self._remote_documents, query))

        ambiguous: list[AmbiguousIdentifier] = []
        for field, roots in roots_by_identifier.items():
            if len(roots) > self.config.max_documents_per_identifier:
                values = sorted(searched_values.get(field, set())) if field else []
                logger.warning(
                    "%s matched %d Kramerius documents for %s — withholding them for "
                    "review; an identifier shared by several documents is a metadata "
                    "error on the Kramerius side",
                    field.value if field else "Unattributed hits",
                    len(roots),
                    values or "-",
                )
                ambiguous.append(
                    AmbiguousIdentifier(field=field, values=values, pids=sorted(roots))
                )
                continue

            links.update(roots)

        for pid in current_kramerius_pids:
            local_available = self.harvest_ready
            try:
                docs = (
                    await asyncio.to_thread(self._local_documents_by_pid, pid)
                    if local_available
                    else []
                )
            except HarvestStorageUnavailable:
                logger.info("Harvested Kramerius data became unavailable; using Solr")
                local_available = False
                docs = []
            if local_available and not docs:
                # Full harvests intentionally omit pages and other irrelevant models.
                # A MARC record may still contain such a PID, so absence is unknown and
                # needs one targeted Solr check to preserve existing-link validation.
                logger.debug("PID %s is absent from harvested models; checking Solr", pid)
            if not local_available or not docs:
                docs = await asyncio.to_thread(self._remote_documents, F(KrameriusField.Pid, pid))
            if not docs:
                continue

            doc = docs[0]

            # Solr declares all three of these optional and leaves them out of
            # a document it holds incompletely. Reading them as given put a
            # None where this validator promises an int: `doc.level != 0` is
            # true for a missing level, so the document was filed as "below the
            # top" with `level=None`, and the reader downstream asks
            # `link.level > 0` — which raises rather than compares. The
            # harvested path has always read a missing level as 0 (see where
            # `_store_documents` builds its rows); this reads it the same way.
            if doc.model_path is None or doc.own_pid_path is None:
                logger.debug("PID %s came back without its hierarchy; skipping", pid)
                continue

            level = doc.level or 0

            if level != 0:
                links[pid] = FoundKrameriusLink(
                    pid,
                    model=Model(doc.model_path.split("/")[-1]),
                    level=level,
                    top_level_pid=doc.own_pid_path.split("/")[0],
                )
                continue

            root_pid = doc.own_pid_path.split("/")[0]
            # Root model is the first element of the path, not the leaf's.
            root_model = Model(doc.model_path.split("/")[0])
            has_wrong_model = root_model not in VALID_TOP_LEVEL_MODELS

            links[root_pid] = FoundKrameriusLink(root_pid, root_model, has_wrong_model)

        return list(links.values()), ambiguous

    async def run(self, record: MarcRecord) -> list[ValidationResult]:
        current_kramerius_pids: list[str] = []
        pid_field_index: dict[str, int] = {}
        # PIDs extracted from URLs with wrong path or wrong server
        url_issue_pids: dict[str, dict] = {}
        results: list[ValidationResult] = []

        def add_result(
            status: ValidityStatus = ValidityStatus.Invalid,
            reason: str | None = None,
            params: dict | None = None,
            field_index: int | None = None,
        ):
            results.append(
                ValidationResult(
                    status=status,
                    target=ValidationTarget(
                        tag=VALIDATION_FIELD.tag,
                        codes=VALIDATION_FIELD.codes,
                        field_index=field_index,
                    ),
                    reason=reason,
                    params=params,
                )
            )

        for field_idx, vf in enumerate(self._queries_for(record).elocation_fields):
            if not any(self.link_text_regex.match(v) for v in vf.subfields.get("y", [])):
                if not any(self.url_to_pid_regex.match(v) for v in vf.subfields.get("u", [])):
                    continue

                add_result(
                    status=ValidityStatus.ForReview,
                    reason="missing_link_text",
                    params={"pattern": self.config.link_text_pattern},
                    field_index=field_idx,
                )

            for v in vf.subfields.get("u", []):
                match = self.url_to_pid_regex.search(v)

                if match:
                    pid = match.group("pid")
                    current_kramerius_pids.append(pid)
                    pid_field_index.setdefault(pid, field_idx)
                    continue

                if not self.own_host_regex.match(v.strip()):
                    # Another institution's digital library. Its PID is not ours
                    # to look up — the same uuid existing in our index does not
                    # make their link wrong — and its URL format is their
                    # business, so the link is recorded and left alone.
                    add_result(
                        status=ValidityStatus.AdditionalInfo,
                        reason="foreign_digital_library",
                        params={"value": v},
                        field_index=field_idx,
                    )
                    continue

                wrong_path_match = self.url_to_pid_wrong_path_regex.search(v)

                if wrong_path_match:
                    pid = wrong_path_match.group("pid")
                    current_kramerius_pids.append(pid)
                    pid_field_index.setdefault(pid, field_idx)
                    url_issue_pids[pid] = {
                        "type": "wrong_path",
                        "value": v,
                        "field_index": field_idx,
                    }
                    continue

                fallback_match = self.url_to_pid_fallback_regex.search(v)

                if fallback_match:
                    pid = fallback_match.group("pid")
                    current_kramerius_pids.append(pid)
                    pid_field_index.setdefault(pid, field_idx)
                    url_issue_pids[pid] = {
                        "type": "wrong_server",
                        "value": v,
                        "field_index": field_idx,
                    }
                    continue

                add_result(
                    reason="invalid_link_format",
                    params={
                        "value": v,
                        "url": self.config.kramerius_client_url,
                    },
                    field_index=field_idx,
                )

        found_kramerius_links, ambiguous_identifiers = await self.find_kramerius_links(
            record, current_kramerius_pids
        )

        for ambiguous in ambiguous_identifiers:
            add_result(
                status=ValidityStatus.ForReview,
                reason="identifier_matches_multiple_documents",
                params={
                    "identifier": ambiguous.field.value if ambiguous.field else "-",
                    "values": ", ".join(ambiguous.values) or "-",
                    "count": str(len(ambiguous.pids)),
                    "pids": ", ".join(ambiguous.pids[:PIDS_IN_REVIEW_SAMPLE]),
                },
            )

        if not current_kramerius_pids and not found_kramerius_links:
            if not results:
                add_result(
                    status=ValidityStatus.Valid,
                    reason="no_links_found_or_expected",
                )

            return results

        found_kramerius_pids = []
        valid_kramerius_pids = []

        for link in found_kramerius_links:
            found_kramerius_pids.append(link.pid)

            if link.level > 0:
                params = {
                    "pid": link.pid,
                    "model": link.model.value,
                    "level": str(link.level),
                }
                if link.top_level_pid:
                    params["top_level_pid"] = link.top_level_pid
                add_result(
                    reason="non_top_level_document",
                    params=params,
                    field_index=pid_field_index.get(link.pid),
                )

            elif link.has_wrong_model:
                add_result(
                    status=ValidityStatus.AdditionalInfo,
                    reason="non_linkable_model",
                    field_index=pid_field_index.get(link.pid),
                    params={
                        "pid": link.pid,
                        "model": link.model.value,
                    },
                )

            else:
                valid_kramerius_pids.append(link.pid)

        current_set = set(current_kramerius_pids)
        found_set = set(found_kramerius_pids)
        valid_set = set(valid_kramerius_pids)

        for pid in current_set & valid_set:
            issue = url_issue_pids.get(pid)
            if issue:
                if issue["type"] == "wrong_path":
                    reason = "wrong_path_found"
                    status = ValidityStatus.AdditionalInfo
                else:
                    reason = "wrong_server_found"
                    status = ValidityStatus.Invalid
                add_result(
                    status=status,
                    reason=reason,
                    params={
                        "pid": pid,
                        "value": issue["value"],
                        "url": self.config.kramerius_client_url,
                    },
                    field_index=issue["field_index"],
                )
            else:
                add_result(
                    status=ValidityStatus.Valid,
                    reason="valid_link",
                    params={"pid": pid},
                    field_index=pid_field_index.get(pid),
                )

        for pid in current_set - found_set:
            issue = url_issue_pids.get(pid)
            if issue:
                if issue["type"] == "wrong_path":
                    reason = "wrong_path_not_found"
                    status = ValidityStatus.AdditionalInfo
                else:
                    reason = "wrong_server_not_found"
                    status = ValidityStatus.Invalid
                add_result(
                    status=status,
                    reason=reason,
                    params={
                        "pid": pid,
                        "value": issue["value"],
                        "url": self.config.kramerius_client_url,
                    },
                    field_index=issue["field_index"],
                )
            else:
                add_result(
                    reason="link_not_found",
                    params={"pid": pid},
                    field_index=pid_field_index.get(pid),
                )

        for pid in valid_set - current_set:
            add_result(reason="missing_link_in_marc", params={"pid": pid})

        return results

    # ── report generation ──────────────────────────────────────────────────
    #
    # Turn the stored not-valid results into Aleph sequential (.seq) repair
    # files (REPLACE-ALL mode: every 856 for a sysno is wiped and reloaded from
    # the emitted lines) plus a delete list for sysnos left with no 856 fields.
    # All changes for one record are grouped and applied in a single pass so
    # conflicting edits to the same 856 set do not overwrite each other.
    #
    # reason → action:
    #   missing_link_in_marc  → add a new correct 856
    #   wrong_server_found    → replace $u at field_index with the correct URL
    #   wrong_path_found      → replace $u at field_index with the correct URL
    #   wrong_path_not_found  → replace $u at field_index with the correct URL
    #   missing_link_text     → add $y (standard link text) at field_index
    #   link_not_found        → remove the broken field at field_index
    #   non_top_level_document → replace $u with the document's own top level
    #
    # The URL fixes rewrite $u in place rather than dropping the field and adding a
    # replacement, so a cataloguer's $x (digitisation project) and $z (volume) survive
    # the repair. Neither is written for a *new* link: the project is recorded nowhere in
    # the Kramerius index, and a volume designation exists only inside the document title,
    # where parsing it would risk writing a wrong $z into the catalogue.
    # Non-repairable reasons (invalid_link_format, wrong_server_not_found,
    # non_linkable_model, foreign_digital_library,
    # identifier_matches_multiple_documents) are left untouched. A link into
    # another institution's digital library is deliberately among them: it is
    # not addressed to our Kramerius and is none of our business to rewrite.

    def _make_url(self, params: dict[str, str]) -> str:
        pid = params.get("pid", "")
        template = params.get("url") or self.config.kramerius_client_url
        return template.replace("{pid}", pid)

    def _build_changes(self, results: Iterable[ValidationResult]) -> dict:
        changes: dict = {"modifications": [], "removals": set(), "additions": []}
        for result in results:
            reason = result.reason
            params = result.params or {}
            field_index = result.target.field_index

            if reason == "missing_link_in_marc":
                changes["additions"].append({"u": self._make_url(params), "y": STANDARD_LINK_TEXT})
            elif reason in ("wrong_server_found", "wrong_path_found", "wrong_path_not_found"):
                changes["modifications"].append(
                    {
                        "field_index": field_index,
                        "action": "replace_u",
                        "new_u": self._make_url(params),
                    }
                )
            elif reason == "non_top_level_document" and params.get("top_level_pid"):
                # The link resolves, just to a page or a volume inside the
                # document. Point it at the top of that same hierarchy rather
                # than dropping it: the cataloguer found the right object.
                changes["modifications"].append(
                    {
                        "field_index": field_index,
                        "action": "replace_u",
                        "new_u": self._make_url({**params, "pid": params["top_level_pid"]}),
                    }
                )
            elif reason == "missing_link_text":
                changes["modifications"].append(
                    {"field_index": field_index, "action": "add_y", "new_y": STANDARD_LINK_TEXT}
                )
            elif reason == "link_not_found" and field_index is not None:
                changes["removals"].add(field_index)
            # other reasons are not auto-repairable — leave the field as-is
        return changes

    def _apply_changes(
        self,
        fields: list[VariableField],
        changes: dict,
        errors: list[dict],
        catalog_record_id: str,
    ) -> list[VariableField]:
        # Step 1 — in-place modifications (indices stay valid).
        for mod in changes["modifications"]:
            idx = mod["field_index"]
            if idx is None or idx >= len(fields):
                errors.append(
                    {
                        "catalog_record_id": catalog_record_id,
                        "error": (
                            f"modification field_index {idx} out of range "
                            f"({len(fields)} 856 fields) — skipping"
                        ),
                    }
                )
                continue
            if mod["action"] == "replace_u":
                fields[idx].subfields["u"] = [mod["new_u"]]
            elif mod["action"] == "add_y":
                fields[idx].subfields["y"] = [mod["new_y"]]

        # Step 2 — drop removed fields (by original index).
        removals = changes["removals"]
        kept = [f for i, f in enumerate(fields) if i not in removals]

        # Step 3 — append additions, skipping any $u already present (Aleph
        # replaces all 856, so a duplicate $u would commit a duplicate link).
        existing_us = {u for f in kept for u in f.subfields.get("u", [])}
        for add in changes["additions"]:
            if add["u"] in existing_us:
                continue
            kept.append(
                VariableField(ind1="4", ind2="1", subfields={"u": [add["u"]], "y": [add["y"]]})
            )
            existing_us.add(add["u"])

        return kept

    @staticmethod
    def _field_to_seq_line(sysno: str, field: VariableField) -> str:
        ind1 = field.ind1 or " "
        ind2 = field.ind2 or " "
        subfields = "".join(
            f"$${code}{value}" for code, values in field.subfields.items() for value in values
        )
        return f"{sysno} {VALIDATION_FIELD.tag}{ind1}{ind2} L {subfields}"

    def generate_report(self, records: Iterable[ReportInput]) -> list[ReportFile]:
        seq_lines_by_base: dict[str, list[str]] = defaultdict(list)
        delete_sysnos_by_base: dict[str, list[str]] = defaultdict(list)
        errors: list[dict] = []

        for record in records:
            try:
                # 'MZK01-001974304' → doc number '001974304'
                doc_number = record.catalog_record_id.split("-", 1)[-1]
                sysno = doc_number.zfill(9)

                changes = self._build_changes(record.results)
                if not (changes["modifications"] or changes["removals"] or changes["additions"]):
                    # No repairable results for this record — leave it alone.
                    continue

                fields = record.marc.variable_fields.query_fields('.["856"][]?')
                final_fields = self._apply_changes(
                    list(fields), changes, errors, record.catalog_record_id
                )

                if final_fields:
                    for field in final_fields:
                        seq_lines_by_base[record.base].append(self._field_to_seq_line(sysno, field))
                else:
                    # Every 856 removed, none added — needs deletion.
                    delete_sysnos_by_base[record.base].append(sysno)
            except Exception as exc:  # noqa: BLE001 - report, don't abort the batch
                errors.append({"catalog_record_id": record.catalog_record_id, "error": str(exc)})

        report_files: list[ReportFile] = []
        for base, lines in sorted(seq_lines_by_base.items()):
            report_files.append(
                ReportFile(
                    filename=f"aleph_seq_{base}.seq",
                    content=("\n".join(lines) + "\n").encode("utf-8"),
                    content_type="text/plain",
                )
            )
        for base, sysnos in sorted(delete_sysnos_by_base.items()):
            report_files.append(
                ReportFile(
                    filename=f"aleph_delete_856_{base}.txt",
                    content=("\n".join(sorted(sysnos)) + "\n").encode("utf-8"),
                    content_type="text/plain",
                )
            )
        if errors:
            report_files.append(
                ReportFile(
                    filename="errors.json",
                    content=json.dumps(errors, indent=2, ensure_ascii=False).encode("utf-8"),
                    content_type="application/json",
                )
            )

        return report_files

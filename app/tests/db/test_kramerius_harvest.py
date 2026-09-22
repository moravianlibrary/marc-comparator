import asyncio
from collections.abc import Iterable
from typing import cast

import pytest
from kramerius.client.search import SearchClient
from kramerius.schemas import KrameriusDocument
from marc_comparator.harvest import HarvestContext, HarvestStorage
from marc_comparator.validators.kramerius_links import (
    DOCUMENTS_TABLE,
    IDENTIFIERS_TABLE,
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from marcdantic import MarcRecord
from sqlalchemy import text

pytestmark = pytest.mark.db

SCHEMA = "plugin_kramerius_harvest_test"
LEADER = "00000nam a2200000 a 4500"


@pytest.fixture(autouse=True)
def run_thread_calls_inline(monkeypatch):
    """The restricted test sandbox cannot start executor threads."""

    async def inline(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", inline)


def raw_document(
    name: str,
    *,
    model: str = "monograph",
    isbn: Iterable[str] = (),
    nbn: Iterable[str] = (),
) -> dict:
    pid = f"uuid:{name}"
    return {
        "compositeId": f"collection/{pid}",
        "pid": pid,
        "model": model,
        "own_pid_path": pid,
        "own_model_path": model,
        "level": 0,
        "id_isbn": list(isbn),
        "id_ccnb": list(nbn),
        "indexed": "2026-09-18T10:00:00.000Z",
    }


def marc_record(*, isbn: str | None = None, nbn: str | None = None) -> MarcRecord:
    variable_fields = {}
    if isbn:
        variable_fields["020"] = [{"ind1": " ", "ind2": " ", "subfields": {"a": [isbn]}}]
    if nbn:
        variable_fields["015"] = [{"ind1": " ", "ind2": " ", "subfields": {"a": [nbn]}}]
    return MarcRecord.model_validate(
        {
            "leader": LEADER,
            "fixed_fields": {
                "001": "000000001",
                "005": "20200101000000.0",
                "008": "200101s2020    xr            000 0 cze d",
            },
            "variable_fields": variable_fields,
        }
    )


@pytest.fixture
def harvest_engine(db_engine):
    with db_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{SCHEMA}"'))
        KrameriusLinksValidator.harvest_metadata(SCHEMA).create_all(connection)
    yield db_engine
    with db_engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{SCHEMA}" CASCADE'))


async def harvest_pages(plugin, engine, pages, watermark=None):
    async def cursor_pages(query):
        for page in pages:
            if isinstance(page, BaseException):
                raise page
            yield page, sum(len(p) for p in pages if isinstance(p, list))

    plugin._solr_cursor_pages = cursor_pages  # type: ignore[method-assign]
    progress = []
    with engine.begin() as connection:
        return await plugin.harvest(
            HarvestContext(
                connection=connection,
                schema=SCHEMA,
                progress=lambda done, total=None: progress.append((done, total)),
                watermark=watermark,
            )
        )


def comparable(result):
    links, ambiguous = result
    return (
        sorted((link.pid, link.model.value, link.has_wrong_model, link.level) for link in links),
        sorted(
            (
                item.field.value if item.field else None,
                tuple(item.values),
                tuple(item.pids),
            )
            for item in ambiguous
        ),
    )


@pytest.mark.asyncio
async def test_harvested_lookup_matches_remote_and_makes_no_network_call(harvest_engine):
    isbn = "978-80-0000-000-1"
    nbn = "cnb000000001"
    raw = [
        raw_document("book", isbn=[isbn], nbn=[nbn]),
        raw_document("pollution", nbn=[nbn]),
    ]
    plugin = KrameriusLinksValidator(KrameriusLinksValidatorConfig())

    class RemoteSearch:
        def search(self, query, fl=None):
            return [KrameriusDocument.model_validate(document) for document in raw]

    plugin.client.Search = cast(SearchClient, RemoteSearch())
    record = marc_record(isbn=isbn, nbn=nbn)
    remote_result = await plugin.find_kramerius_links(record, [])

    result = await harvest_pages(plugin, harvest_engine, [raw[:1], raw[1:]])
    assert result.records == 2
    plugin.bind_harvest_storage(
        HarvestStorage(
            schema=SCHEMA,
            source_identity=plugin.harvest_source_identity(),
            connection=harvest_engine.connect,
        )
    )

    class NetworkMustNotBeUsed:
        def search(self, query, fl=None):
            raise AssertionError("ready local identifier lookup called Solr")

    plugin.client.Search = cast(SearchClient, NetworkMustNotBeUsed())
    local_result = await plugin.find_kramerius_links(record, [])

    assert comparable(local_result) == comparable(remote_result)


@pytest.mark.asyncio
async def test_incremental_replacement_removes_old_identifiers_and_excluded_models(
    harvest_engine,
):
    plugin = KrameriusLinksValidator(KrameriusLinksValidatorConfig())
    original = [
        raw_document("changed", isbn=["old-isbn"]),
        raw_document("now-page", nbn=["old-nbn"]),
    ]
    await harvest_pages(plugin, harvest_engine, [original])

    changed = [
        raw_document("changed", isbn=["new-isbn"]),
        raw_document("now-page", model="page", nbn=["old-nbn"]),
    ]
    watermark = "2026-09-18T09:00:00.000Z"
    await harvest_pages(plugin, harvest_engine, [changed], watermark=watermark)
    # Inclusive overlap makes retries expected; replacement must remain idempotent.
    await harvest_pages(plugin, harvest_engine, [changed], watermark=watermark)

    with harvest_engine.connect() as connection:
        documents = (
            connection.execute(text(f'SELECT pid FROM "{SCHEMA}"."{DOCUMENTS_TABLE}" ORDER BY pid'))
            .scalars()
            .all()
        )
        identifiers = connection.execute(
            text(f'SELECT kind, value FROM "{SCHEMA}"."{IDENTIFIERS_TABLE}" ORDER BY kind, value')
        ).all()

    assert documents == ["uuid:changed"]
    assert identifiers == [("id_isbn", "new-isbn")]


@pytest.mark.asyncio
async def test_failed_later_page_rolls_back_earlier_replacement(harvest_engine):
    plugin = KrameriusLinksValidator(KrameriusLinksValidatorConfig())
    await harvest_pages(plugin, harvest_engine, [[raw_document("book", isbn=["old"])]])

    with pytest.raises(ConnectionError, match="page failed"):
        await harvest_pages(
            plugin,
            harvest_engine,
            [[raw_document("book", isbn=["new"])], ConnectionError("page failed")],
            watermark="2026-09-18T09:00:00.000Z",
        )

    with harvest_engine.connect() as connection:
        values = (
            connection.execute(text(f'SELECT value FROM "{SCHEMA}"."{IDENTIFIERS_TABLE}"'))
            .scalars()
            .all()
        )
    assert values == ["old"]

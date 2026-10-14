import asyncio
from typing import cast
from unittest.mock import MagicMock

import pytest
from marc_comparator.harvest import HarvestContext
from marc_comparator.validators.kramerius_links import (
    DOCUMENTS_TABLE,
    HARVEST_PAGE_SIZE,
    IDENTIFIERS_TABLE,
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@pytest.fixture(autouse=True)
def run_thread_calls_inline(monkeypatch):
    """The restricted unit-test sandbox cannot start executor threads."""

    async def inline(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", inline)


def raw_document(composite_id: str, *, model: str = "monograph") -> dict:
    return {
        "compositeId": composite_id,
        "pid": f"uuid:{composite_id}",
        "model": model,
        "own_pid_path": f"uuid:{composite_id}",
        "own_model_path": model,
        "level": 0,
        "id_isbn": [f"isbn-{composite_id}"],
        "indexed": "2026-09-18T10:00:00.000Z",
    }


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class CursorSession:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.params = []

    def get(self, url, *, params, timeout):
        self.params.append(params)
        return Response(next(self.pages))

    def close(self):
        return None


def validator(**config) -> KrameriusLinksValidator:
    return KrameriusLinksValidator(KrameriusLinksValidatorConfig(search_page_size=2, **config))


def scripted_http(plugin: KrameriusLinksValidator, session: object) -> None:
    """Swap in a scripted HTTP session; only ``get`` and ``close`` are exercised."""

    plugin.client.Search._session = cast(Session, session)


@pytest.mark.asyncio
async def test_full_harvest_streams_cursor_pages_and_filters_excluded_models():
    plugin = validator()
    session = CursorSession(
        [
            {
                "response": {
                    "numFound": 2,
                    "docs": [raw_document("one"), raw_document("page", model="page")],
                },
                "nextCursorMark": "after-one",
            },
            {
                "response": {"numFound": 2, "docs": []},
                "nextCursorMark": "after-one",
            },
        ]
    )
    scripted_http(plugin, session)
    replaced = []
    plugin._replace_harvest_page = lambda connection, schema, changed, stored: replaced.append(  # type: ignore[method-assign]
        (changed, stored)
    )
    progress = MagicMock()

    result = await plugin.harvest(
        HarvestContext(connection=MagicMock(), schema="plugin_test", progress=progress)
    )

    assert result.records == 2
    assert result.watermark is not None
    assert result.watermark.endswith("Z")
    assert [doc["compositeId"] for doc in replaced[0][0]] == ["one", "page"]
    assert [doc["compositeId"] for doc in replaced[0][1]] == ["one"]
    assert session.params[0]["cursorMark"] == "*"
    assert session.params[1]["cursorMark"] == "after-one"
    assert session.params[0]["sort"] == "compositeId asc"
    assert session.params[0]["rows"] == HARVEST_PAGE_SIZE
    assert "model:" in session.params[0]["q"]
    progress.assert_called_once_with(2, 2)


@pytest.mark.asyncio
async def test_empty_incremental_harvest_advances_inclusive_watermark():
    plugin = validator()
    session = CursorSession(
        [
            {
                "response": {"numFound": 0, "docs": []},
                "nextCursorMark": "*",
            }
        ]
    )
    scripted_http(plugin, session)
    progress = MagicMock()
    watermark = "2026-09-17T00:00:00.000Z"

    result = await plugin.harvest(
        HarvestContext(
            connection=MagicMock(),
            schema="plugin_test",
            progress=progress,
            watermark=watermark,
        )
    )

    assert result.records == 0
    assert result.watermark != watermark
    assert f"indexed:[{watermark} TO " in session.params[0]["q"]
    # Incremental reads all changed models so model changes can delete old rows.
    assert "model:" not in session.params[0]["q"]
    progress.assert_called_once_with(0, 0)


@pytest.mark.asyncio
async def test_cursor_network_failure_is_not_published_as_success():
    plugin = validator()

    class FailedSession:
        def get(self, *args, **kwargs):
            raise ConnectionError("Solr unavailable")

        def close(self):
            return None

    scripted_http(plugin, FailedSession())

    with pytest.raises(ConnectionError, match="Solr unavailable"):
        await plugin.harvest(
            HarvestContext(connection=MagicMock(), schema="plugin_test", progress=MagicMock())
        )


@pytest.mark.asyncio
async def test_partial_cursor_response_is_rejected():
    plugin = validator()
    scripted_http(
        plugin,
        CursorSession(
            [
                {
                    "responseHeader": {"partialResults": True},
                    "response": {"numFound": 1, "docs": [raw_document("one")]},
                    "nextCursorMark": "*",
                }
            ]
        ),
    )

    with pytest.raises(RuntimeError, match="partial cursor results"):
        await plugin.harvest(
            HarvestContext(connection=MagicMock(), schema="plugin_test", progress=MagicMock())
        )


def test_metadata_has_qualified_document_and_identifier_tables():
    metadata = KrameriusLinksValidator.harvest_metadata("plugin_test")

    assert metadata.schema == "plugin_test"
    assert set(metadata.tables) == {
        f"plugin_test.{DOCUMENTS_TABLE}",
        f"plugin_test.{IDENTIFIERS_TABLE}",
    }
    assert all(table.schema == "plugin_test" for table in metadata.tables.values())


def test_source_identity_tracks_source_but_not_presentation_settings():
    first = validator(kramerius_client_url="https://reader-one.example/{pid}")
    same_source = validator(kramerius_client_url="https://reader-two.example/{pid}")
    other_source = validator(kramerius_host="https://other.example/search")

    assert first.harvest_source_identity() == same_source.harvest_source_identity()
    assert first.harvest_source_identity() != other_source.harvest_source_identity()


# ── search retry policy ──────────────────────────────────────────────────────


def mounted_retry(plugin: KrameriusLinksValidator) -> Retry:
    session = plugin.client.Search._session
    adapter = cast(HTTPAdapter, session.get_adapter("https://api.kramerius.mzk.cz/"))
    return cast(Retry, adapter.max_retries)


def test_the_search_session_does_not_keep_solrifys_retry_defaults():
    """One unreachable PID must not be able to stall a run for the best part of an hour.

    Solrify mounts ten retries at a backoff factor of four and the Kramerius
    client never overrides them, so against a 180 s read timeout a single dead
    PID cost eleven attempts plus twelve minutes of sleeping — 2700 s, which
    is exactly the gap seen five times in one night's validation log.
    """

    retry = mounted_retry(validator())

    assert retry.total == 3
    assert retry.backoff_factor == 1.0
    # The defaults this exists to displace.
    assert (retry.total, retry.backoff_factor) != (10, 4)


def test_a_read_timeout_is_retried_less_than_a_server_error():
    """They are not the same failure.

    A 503 is a moment of load worth waiting out and costs nothing to repeat.
    A read timeout means the request was accepted and never answered, so each
    further attempt burns the whole timeout and rarely changes the answer.
    """

    retry = mounted_retry(validator())

    assert retry.read == 1
    assert retry.status is not None
    assert retry.read < retry.status


def test_the_retry_policy_is_configurable():
    retry = mounted_retry(
        validator(search_retries=7, search_read_retries=4, search_retry_backoff=0.5)
    )

    assert (retry.total, retry.read, retry.backoff_factor) == (7, 4, 0.5)


def test_a_lookup_waits_far_less_than_a_harvest_page():
    """One number cannot serve both requests.

    A harvest page asks for a thousand documents and needs minutes; a lookup
    asks about one PID and answers in milliseconds. While they shared a
    timeout, the wait sized for the thousand was what a single dead PID cost,
    once per retry.
    """

    config = KrameriusLinksValidatorConfig()

    assert config.lookup_timeout < config.harvest_timeout
    assert config.harvest_timeout == 180, "the harvest page keeps the wait it needs"


def test_the_search_client_is_built_with_the_lookup_timeout():
    plugin = validator()

    assert plugin.client.Search._timeout == plugin.config.lookup_timeout


def test_the_worst_a_dead_pid_can_cost_stays_under_a_minute():
    """The number this whole policy exists to hold down.

    Eleven attempts at 180 s plus twelve minutes of backoff was 45 minutes,
    seen five times in one night's log while the run did nothing else.
    """

    plugin = validator()
    retry = mounted_retry(plugin)

    assert retry.read is not None
    worst = (retry.read + 1) * plugin.config.lookup_timeout
    assert worst < 60, f"a dead PID would stall the run for {worst}s"

"""A linking pass refuses to start without the linkers it was told to use.

The failure this pins is not hypothetical. A local install ran a full pass
with `marcxml-dump` configured but absent from the processing settings and
wrote 223,176 `NoCandidate` rows — one per record, each asserting that the
catalogue holds no counterpart, for records nobody had looked up.
"""

import pytest
from fastapi import HTTPException
from marc_comparator.authority_linkers import AuthorityLinker

from authority_linking.models import AuthorityLinkingSettings
from authority_linking.tasks import (
    AuthorityLinkerUnavailable,
    AuthorityLinkingNotConfigured,
    load_authority_linkers,
)
from catalog_records.models import ProcessRecordsSettings
from entities.settings import Settings, SettingsScope


@pytest.fixture
def linking_settings(db_session):
    Settings.upsert(
        db_session,
        SettingsScope.AuthorityLinking,
        AuthorityLinkingSettings(),
        AuthorityLinkingSettings,
    )
    return db_session


def test_a_linker_whose_dump_was_never_harvested_stops_the_pass(linking_settings):
    """The dump linker reads a harvested copy. Without one it cannot answer,
    and a pass that drops it silently reports every record as unmatched."""

    with pytest.raises(AuthorityLinkerUnavailable) as caught:
        load_authority_linkers(linking_settings, [AuthorityLinker.MarcXmlDump])

    assert caught.value.linkers == ["marcxml-dump"]
    # The message has to be actionable: an operator reading the failed task
    # needs to know which of the two ways out of this they want.
    assert "Harvest them" in str(caught.value)


@pytest.mark.asyncio
async def test_manual_process_request_refuses_an_unready_dump(linking_settings, monkeypatch):
    from catalog_records import service
    from catalog_records.models import RecordFilter

    Settings.upsert(
        linking_settings,
        SettingsScope.ProcessRecords,
        ProcessRecordsSettings(authority_linkers=[AuthorityLinker.MarcXmlDump]),
        ProcessRecordsSettings,
    )

    async def unexpected_enqueue(*_args):
        pytest.fail("processing was queued before its required dataset was ready")

    monkeypatch.setattr(service, "enqueue_task", unexpected_enqueue)
    with pytest.raises(HTTPException) as caught:
        await service.process_records(RecordFilter(), "operator", linking_settings)

    assert caught.value.status_code == 409
    assert "marcxml-dump" in caught.value.detail


def test_a_linker_that_needs_no_harvest_runs(linking_settings):
    """knihovny.cz asks a remote service per record, so there is nothing to
    harvest and nothing to be missing. The guard must not catch it."""

    loaded = load_authority_linkers(linking_settings, [AuthorityLinker.KnihovnyCz])

    assert [linker.linker for linker in loaded] == [AuthorityLinker.KnihovnyCz]


def test_one_unready_linker_stops_the_pass_even_beside_a_ready_one(linking_settings):
    """The answer is per record and nobody knows in advance which records the
    missing linker would have placed, so a partial set is not a smaller run —
    it is the same run with a wrong answer for an unknown subset."""

    with pytest.raises(AuthorityLinkerUnavailable):
        load_authority_linkers(
            linking_settings, [AuthorityLinker.MarcXmlDump, AuthorityLinker.KnihovnyCz]
        )


def test_no_stored_settings_is_refused_rather_than_reported_as_done(db_session):
    with pytest.raises(AuthorityLinkingNotConfigured):
        load_authority_linkers(db_session, [AuthorityLinker.KnihovnyCz])


def test_the_dump_linker_is_on_by_default():
    """It does the overwhelming majority of the linking and was left out of
    this default for two weeks after it was written."""

    assert AuthorityLinker.MarcXmlDump in ProcessRecordsSettings().authority_linkers


def test_the_dump_linker_is_asked_first():
    """Order is priority. The indexed local lookup settles most records, so
    asking the remote service first spends an HTTP call to lose a race."""

    assert ProcessRecordsSettings().authority_linkers[0] == AuthorityLinker.MarcXmlDump


class TestAClaimAsksForTheLinkersAPassWouldUse:
    """`_reapply` used to derive its linker list from "does this linker have a
    config object", which every linker does — the field carries a default. It
    therefore asked for linkers the operator had switched off, and on an
    install without their harvest the pass it enqueued took the record's rows
    with it on the way down."""

    async def test_the_claim_pass_asks_for_the_configured_linkers(self, db_session, monkeypatch):
        from authority_linking import service

        Settings.upsert(
            db_session,
            SettingsScope.ProcessRecords,
            ProcessRecordsSettings(authority_linkers=[AuthorityLinker.KnihovnyCz]),
            ProcessRecordsSettings,
        )
        enqueued: list[list[AuthorityLinker]] = []

        async def capture(task, _db_session):
            enqueued.append(list(task.data["linkers"]))
            return None

        monkeypatch.setattr(service, "enqueue_task", capture)
        await service._reapply(db_session, "someone", "MZK01-000000001", "SKC")

        assert enqueued == [[AuthorityLinker.KnihovnyCz]]

    async def test_no_processing_settings_leaves_the_claim_standing(self, db_session, monkeypatch):
        """Nothing to re-link against is not a reason to lose the verdict."""
        from authority_linking import service

        called = False

        async def capture(task, _db_session):
            nonlocal called
            called = True
            return None

        monkeypatch.setattr(service, "enqueue_task", capture)
        assert await service._reapply(db_session, "someone", "MZK01-000000001", "SKC") is None
        assert not called

"""Lookup connections stay independent of task sessions and protect rebuilds."""

import logging

import pytest
from marc_comparator.harvest import HarvestCapable, HarvestResult, HarvestStorageUnavailable
from sqlalchemy import Column, Integer, MetaData, Table, delete, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from entities.plugin_harvest import PluginHarvestState
from entities.settings import SettingsSchema, SettingsScope
from harvest import storage
from harvest.registry import HarvestablePlugin, complete_harvest, ensure_schema


class LookupPlugin(HarvestCapable):
    needs_harvest = True

    def harvest_source_identity(self):
        return "lookup-source"

    @classmethod
    def harvest_metadata(cls, schema):
        metadata = MetaData(schema=schema)
        Table("documents", metadata, Column("id", Integer, primary_key=True))
        return metadata


PLUGIN = HarvestablePlugin("lookup-test", LookupPlugin, SettingsScope.Validation, SettingsSchema)


@pytest.fixture
def dataset(db_engine):
    with Session(db_engine) as session, session.begin():
        ensure_schema(PLUGIN, session, "lookup-source", force=True)
        session.execute(text("INSERT INTO plugin_lookup_test.documents VALUES (1)"))
        complete_harvest(PLUGIN, session, HarvestResult(records=1), "lookup-source")
    yield db_engine
    with db_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS plugin_lookup_test CASCADE"))
        connection.execute(
            delete(PluginHarvestState).where(PluginHarvestState.plugin == PLUGIN.name)
        )


def test_storage_outlives_task_session(dataset, monkeypatch):
    monkeypatch.setattr(storage, "find_plugin", lambda name: PLUGIN)
    instance = LookupPlugin()
    with Session(dataset) as session:
        assert storage.bind_plugin_storage(
            PLUGIN.name, instance, session, logging.getLogger(__name__)
        )
        session.commit()
    assert instance.harvest_storage is not None
    with instance.harvest_storage.connection() as connection:
        assert connection.scalar(text("SELECT id FROM plugin_lookup_test.documents")) == 1


def test_old_binding_rejects_new_source(dataset):
    with dataset.begin() as connection:
        connection.execute(
            update(PluginHarvestState)
            .where(PluginHarvestState.plugin == PLUGIN.name)
            .values(source_identity="different-source")
        )
    with (
        pytest.raises(HarvestStorageUnavailable),
        storage.lookup_connection(dataset, PLUGIN, "lookup-source"),
    ):
        pytest.fail("A stale source binding must never be yielded")


def test_lookup_blocks_ddl_but_allows_incremental_writes(dataset):
    with storage.lookup_connection(dataset, PLUGIN, "lookup-source") as reader:
        with dataset.begin() as writer:
            writer.execute(text("INSERT INTO plugin_lookup_test.documents VALUES (2)"))
        assert reader.scalar(text("SELECT count(*) FROM plugin_lookup_test.documents")) == 2
        with pytest.raises(DBAPIError) as error, dataset.begin() as rebuilder:
            rebuilder.execute(text("SET LOCAL lock_timeout = '100ms'"))
            rebuilder.execute(text("DROP SCHEMA plugin_lookup_test CASCADE"))
        assert getattr(error.value.orig, "pgcode", None) == "55P03"


def test_missing_tables_raise_storage_unavailable(dataset):
    with dataset.begin() as connection:
        connection.execute(text("DROP TABLE plugin_lookup_test.documents"))
    with (
        pytest.raises(HarvestStorageUnavailable),
        storage.lookup_connection(dataset, PLUGIN, "lookup-source"),
    ):
        pytest.fail("A missing table must trigger remote fallback")

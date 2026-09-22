import contextlib
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from enum import StrEnum
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from marc_comparator.harvest import HarvestCapable, HarvestStorage
from pydantic import BaseModel, Field
from sqlalchemy import Column, Connection, Integer, MetaData, Table

import harvest.registry as registry
from entities.plugin_harvest import PluginHarvestState
from entities.settings import SettingsSchema, SettingsScope
from harvest.registry import (
    HarvestablePlugin,
    HarvestDefinitionError,
    bind_ready_storage,
    dataset_is_ready,
    ensure_schema,
    harvestable_plugins,
    instantiate,
    source_identity_of,
)


class Config(BaseModel):
    endpoint: str = "https://default.example"


class ConfiguredHarvest(HarvestCapable):
    needs_harvest = True
    config_model = Config

    def __init__(self, config: Config) -> None:
        self.config = config

    def harvest_source_identity(self) -> str:
        return self.config.endpoint

    @classmethod
    def harvest_metadata(cls, schema: str) -> MetaData:
        metadata = MetaData(schema=schema)
        Table("records", metadata, Column("id", Integer, primary_key=True))
        return metadata


class PluginKey(StrEnum):
    Example = "example-harvest"


class SettingsModel(SettingsSchema):
    example_harvest: Config | None = Field(alias="example-harvest")


@contextlib.contextmanager
def fake_connection() -> Iterator[Connection]:
    """These tests only pass the factory around; no statement is ever issued."""

    yield cast(Connection, object())


def descriptor(
    name: str = PluginKey.Example.value,
    plugin_cls: type[HarvestCapable] = ConfiguredHarvest,
) -> HarvestablePlugin:
    return HarvestablePlugin(name, plugin_cls, SettingsScope.Validation, SettingsModel)


def test_harvest_capability_defaults_and_storage_binding():
    plugin = HarvestCapable()
    assert plugin.needs_harvest is False
    assert plugin.harvest_ready is False
    assert plugin.harvest_storage is None

    storage = HarvestStorage("plugin_example", "source-v1", fake_connection)
    plugin.bind_harvest_storage(storage)
    assert plugin.harvest_ready is True
    assert plugin.harvest_storage is storage

    plugin.bind_harvest_storage(None)
    assert plugin.harvest_ready is False


def test_sdk_harvest_module_imports_when_sqlalchemy_is_unavailable():
    code = """
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'sqlalchemy' or name.startswith('sqlalchemy.'):
        raise ModuleNotFoundError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
from marc_comparator.harvest import HarvestCapable, HarvestStorage
assert not HarvestCapable().harvest_ready
"""
    result = subprocess.run(
        [sys.executable, "-c", code], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_instantiation_uses_stored_configuration_and_defaults(mocker):
    stored = Config(endpoint="https://stored.example")
    mocker.patch.object(
        registry.Settings,
        "get",
        side_effect=[SimpleNamespace(example_harvest=stored), None],
    )

    first = instantiate(descriptor(), Mock())
    second = instantiate(descriptor(), Mock())

    assert isinstance(first, ConfiguredHarvest)
    assert first.config is stored
    assert isinstance(second, ConfiguredHarvest)
    assert second.config == Config()


def test_discovery_rejects_registry_name_and_normalized_schema_collisions(monkeypatch):
    class OtherKey(StrEnum):
        SameName = "example-harvest"
        SameSchema = "example_harvest"

    class OtherHarvest(ConfiguredHarvest):
        pass

    monkeypatch.setattr(
        registry,
        "_FAMILIES",
        [
            ({PluginKey.Example: ConfiguredHarvest}, SettingsScope.Validation, SettingsModel),
            ({OtherKey.SameName: OtherHarvest}, SettingsScope.AuthorityLinking, SettingsModel),
        ],
    )
    with pytest.raises(HarvestDefinitionError, match="registry name"):
        harvestable_plugins()

    monkeypatch.setattr(
        registry,
        "_FAMILIES",
        [
            ({PluginKey.Example: ConfiguredHarvest}, SettingsScope.Validation, SettingsModel),
            ({OtherKey.SameSchema: OtherHarvest}, SettingsScope.AuthorityLinking, SettingsModel),
        ],
    )
    with pytest.raises(HarvestDefinitionError, match="both map to schema"):
        harvestable_plugins()


def test_metadata_namespace_escape_is_rejected_before_ddl():
    class EscapingHarvest(ConfiguredHarvest):
        @classmethod
        def harvest_metadata(cls, schema: str) -> MetaData:
            metadata = MetaData(schema=schema)
            Table("inside", metadata, Column("id", Integer), schema=schema)
            Table("outside", metadata, Column("id", Integer), schema="public")
            return metadata

    session = Mock()
    session.get.return_value = None

    with pytest.raises(HarvestDefinitionError, match="outside schema"):
        ensure_schema(descriptor(plugin_cls=EscapingHarvest), session, "source-v1")

    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_ensure_schema_leaves_transaction_ownership_with_caller(mocker):
    session = Mock()
    session.get.return_value = None
    mocker.patch.object(MetaData, "create_all")

    assert ensure_schema(descriptor(), session, "source-v1") is True

    session.execute.assert_called()
    session.flush.assert_called_once()
    session.commit.assert_not_called()
    state = session.add.call_args.args[0]
    assert state.source_identity == "source-v1"
    assert state.last_harvest_at is None


def test_readiness_requires_success_and_exact_source_then_binds_storage():
    plugin = descriptor()
    instance = ConfiguredHarvest(Config(endpoint="source-v1"))
    state = PluginHarvestState(
        plugin=plugin.name,
        schema_name=plugin.schema_name,
        schema_version=plugin.schema_version,
        source_identity="source-v1",
        watermark="cursor",
        records=2,
        last_harvest_at=datetime.now(UTC),
    )

    assert source_identity_of(instance) == "source-v1"
    assert dataset_is_ready(plugin, state, "source-v1") is True
    assert bind_ready_storage(plugin, instance, state, fake_connection) is True
    assert instance.harvest_storage == HarvestStorage(
        plugin.schema_name, "source-v1", fake_connection
    )

    instance.config = Config(endpoint="source-v2")
    assert bind_ready_storage(plugin, instance, state, fake_connection) is False
    assert instance.harvest_storage is None

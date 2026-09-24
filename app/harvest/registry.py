"""Discovery and transactional storage management for harvest plugins."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from marc_comparator.authority_linkers import AUTHORITY_LINKER_DISPATCHER
from marc_comparator.harvest import (
    ConnectionFactory,
    HarvestCapable,
    HarvestResult,
    HarvestStorage,
)
from marc_comparator.validators import VALIDATOR_DISPATCHER
from sqlalchemy import MetaData, text
from sqlalchemy.orm import Session

from authority_linking.models import AuthorityLinkingSettings
from entities.plugin_harvest import PluginHarvestState
from entities.settings import Settings, SettingsSchema, SettingsScope
from validation.models import ValidationSettings

type PluginDispatcher = Mapping[Any, type[HarvestCapable]]
type PluginFamily = tuple[PluginDispatcher, SettingsScope, type[SettingsSchema]]

# A new plugin family needs only one entry here.
_FAMILIES: list[PluginFamily] = [
    (VALIDATOR_DISPATCHER, SettingsScope.Validation, ValidationSettings),
    (AUTHORITY_LINKER_DISPATCHER, SettingsScope.AuthorityLinking, AuthorityLinkingSettings),
]

SCHEMA_PREFIX = "plugin_"
_SAFE_SCHEMA = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class HarvestDefinitionError(ValueError):
    """A harvest plugin declaration is unsafe or internally inconsistent."""


class HarvestAlreadyRunningError(RuntimeError):
    """The transaction-scoped lock for this plugin is already held."""


@dataclass(frozen=True, slots=True)
class HarvestablePlugin:
    """Stable application identity and configuration location for a plugin."""

    name: str
    cls: type[HarvestCapable]
    scope: SettingsScope
    settings_model: type[SettingsSchema]

    @property
    def schema_name(self) -> str:
        schema = SCHEMA_PREFIX + self.name.replace("-", "_")
        if not _SAFE_SCHEMA.fullmatch(schema):
            raise HarvestDefinitionError(
                f"Plugin {self.name!r} does not map to a safe PostgreSQL schema name"
            )
        return schema

    @property
    def schema_version(self) -> int:
        version = self.cls.harvest_schema_version
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise HarvestDefinitionError(
                f"Plugin {self.name!r} has invalid harvest schema version {version!r}"
            )
        return version


def harvestable_plugins() -> list[HarvestablePlugin]:
    """Discover plugins and reject ambiguous names, schemas, or classes."""

    plugins: list[HarvestablePlugin] = []
    names: dict[str, HarvestablePlugin] = {}
    schemas: dict[str, HarvestablePlugin] = {}
    classes: dict[type[HarvestCapable], HarvestablePlugin] = {}

    for dispatcher, scope, settings_model in _FAMILIES:
        for key, plugin_cls in dispatcher.items():
            if not getattr(plugin_cls, "needs_harvest", False):
                continue

            name = getattr(key, "value", None)
            if not isinstance(name, str) or not name:
                raise HarvestDefinitionError(
                    f"Harvest plugin key {key!r} must expose a non-empty string value"
                )
            if not issubclass(plugin_cls, HarvestCapable):
                raise HarvestDefinitionError(
                    f"Harvest plugin {name!r} does not inherit HarvestCapable"
                )

            plugin = HarvestablePlugin(name, plugin_cls, scope, settings_model)
            # Evaluate and validate these even when no DDL is currently needed.
            schema = plugin.schema_name
            _ = plugin.schema_version

            if previous := names.get(name):
                raise HarvestDefinitionError(
                    f"Harvest registry name {name!r} is used by both "
                    f"{previous.cls.__name__} and {plugin_cls.__name__}"
                )
            if previous := schemas.get(schema):
                raise HarvestDefinitionError(
                    f"Harvest plugins {previous.name!r} and {name!r} both map to schema {schema!r}"
                )
            if previous := classes.get(plugin_cls):
                raise HarvestDefinitionError(
                    f"Harvest plugin class {plugin_cls.__name__} is registered as both "
                    f"{previous.name!r} and {name!r}"
                )

            names[name] = plugin
            schemas[schema] = plugin
            classes[plugin_cls] = plugin
            plugins.append(plugin)

    return sorted(plugins, key=lambda plugin: plugin.name)


def find_plugin(name: str) -> HarvestablePlugin | None:
    """Find a plugin by its stable registry name."""

    return next((plugin for plugin in harvestable_plugins() if plugin.name == name), None)


def instantiate(plugin: HarvestablePlugin, db_session: Session) -> HarvestCapable:
    """Build a plugin with the same stored configuration used by task paths."""

    config_model = getattr(plugin.cls, "config_model", None)
    if config_model is None:
        return plugin.cls()  # pyright: ignore[reportCallIssue]

    settings = Settings.get(db_session, plugin.scope, plugin.settings_model)
    stored = getattr(settings, plugin.name.replace("-", "_"), None) if settings else None
    config = stored if stored is not None else config_model()
    return plugin.cls(config)  # pyright: ignore[reportCallIssue]


def source_identity_of(instance: HarvestCapable) -> str:
    """Read and validate the plugin-defined source/configuration fingerprint."""

    identity = instance.harvest_source_identity()
    if not isinstance(identity, str) or not identity.strip():
        raise HarvestDefinitionError("Harvest source identity must be a non-empty string")
    return identity


def validated_metadata(plugin: HarvestablePlugin) -> MetaData:
    """Build metadata and prove that every table stays in the assigned schema."""

    schema = plugin.schema_name
    metadata = plugin.cls.harvest_metadata(schema)
    if not isinstance(metadata, MetaData):
        raise HarvestDefinitionError(
            f"Plugin {plugin.name!r} harvest_metadata() did not return MetaData"
        )
    if metadata.schema != schema:
        raise HarvestDefinitionError(
            f"Plugin {plugin.name!r} metadata must use assigned schema {schema!r}"
        )
    if not metadata.tables:
        raise HarvestDefinitionError(f"Plugin {plugin.name!r} declares no harvest tables")

    escaped = sorted(table.fullname for table in metadata.tables.values() if table.schema != schema)
    if escaped:
        raise HarvestDefinitionError(
            f"Plugin {plugin.name!r} declares tables outside schema {schema!r}: "
            + ", ".join(escaped)
        )
    return metadata


def dataset_is_ready(
    plugin: HarvestablePlugin,
    state: PluginHarvestState | None,
    source_identity: str,
) -> bool:
    """Return whether state names a successful, compatible local dataset."""

    return bool(
        state is not None
        and state.plugin == plugin.name
        and state.schema_name == plugin.schema_name
        and state.schema_version == plugin.schema_version
        and state.source_identity == source_identity
        and state.last_harvest_at is not None
    )


def bind_ready_storage(
    plugin: HarvestablePlugin,
    instance: HarvestCapable,
    state: PluginHarvestState | None,
    connection_factory: ConnectionFactory,
) -> bool:
    """Bind compatible storage to an instance, clearing stale bindings otherwise."""

    source_identity = source_identity_of(instance)
    ready = dataset_is_ready(plugin, state, source_identity)
    storage = (
        HarvestStorage(plugin.schema_name, source_identity, connection_factory) if ready else None
    )
    instance.bind_harvest_storage(storage)
    return ready


def ensure_schema(
    plugin: HarvestablePlugin,
    db_session: Session,
    source_identity: str,
    *,
    force: bool = False,
) -> bool:
    """Make plugin tables match current schema and source inside the caller's transaction.

    Returns ``True`` when tables were rebuilt. Metadata is fully validated
    before any destructive DDL. PostgreSQL DDL is transactional, so rolling
    back the caller's transaction restores the prior schema and state.
    """

    if not isinstance(source_identity, str) or not source_identity.strip():
        raise HarvestDefinitionError("Harvest source identity must be a non-empty string")

    state = db_session.get(PluginHarvestState, plugin.name)
    compatible = (
        state is not None
        and state.schema_name == plugin.schema_name
        and state.schema_version == plugin.schema_version
        and state.source_identity == source_identity
    )
    if compatible and not force:
        return False

    # Validation must precede DROP so a bad plugin cannot destroy usable data.
    metadata = validated_metadata(plugin)
    schema = plugin.schema_name
    db_session.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    db_session.execute(text(f'CREATE SCHEMA "{schema}"'))
    metadata.create_all(bind=db_session.connection())

    if state is None:
        state = PluginHarvestState(plugin=plugin.name)
        db_session.add(state)
    state.schema_name = schema
    state.schema_version = plugin.schema_version
    state.source_identity = source_identity
    state.watermark = None
    state.records = 0
    state.total_records = None
    state.last_harvest_at = None
    db_session.flush()
    return True


def complete_harvest(
    plugin: HarvestablePlugin,
    db_session: Session,
    result: HarvestResult,
    source_identity: str,
    *,
    completed_at: datetime | None = None,
) -> PluginHarvestState:
    """Publish successful result metadata without committing the transaction."""

    state = db_session.get(PluginHarvestState, plugin.name)
    if state is None:
        raise RuntimeError(f"Harvest state for plugin {plugin.name!r} has not been initialized")
    if (
        state.schema_name != plugin.schema_name
        or state.schema_version != plugin.schema_version
        or state.source_identity != source_identity
    ):
        raise RuntimeError(f"Harvest state for plugin {plugin.name!r} is not compatible")

    state.watermark = result.watermark
    state.records = result.records
    state.total_records = result.total_records
    state.last_harvest_at = completed_at or datetime.now(UTC)
    db_session.flush()
    return state


def acquire_harvest_lock(plugin: HarvestablePlugin, db_session: Session) -> None:
    """Acquire this plugin's PostgreSQL transaction-scoped advisory lock."""

    digest = hashlib.blake2b(
        f"marc-comparator:harvest:{plugin.name}".encode(), digest_size=8
    ).digest()
    lock_key = int.from_bytes(digest, byteorder="big", signed=True)
    acquired = db_session.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key}
    ).scalar_one()
    if not acquired:
        raise HarvestAlreadyRunningError(f"A harvest for plugin {plugin.name!r} is already running")


def drop_schema(plugin: HarvestablePlugin, db_session: Session) -> None:
    """Remove plugin data and state inside the caller's transaction."""

    db_session.execute(text(f'DROP SCHEMA IF EXISTS "{plugin.schema_name}" CASCADE'))
    state = db_session.get(PluginHarvestState, plugin.name)
    if state is not None:
        db_session.delete(state)
        db_session.flush()

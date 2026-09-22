"""Bind short-lived, source-checked lookup connections to application plugins."""

from collections.abc import Iterator
from contextlib import contextmanager
from logging import Logger

from marc_comparator.harvest import HarvestCapable, HarvestStorageUnavailable
from sqlalchemy import Connection, Engine, select, text
from sqlalchemy.exc import DBAPIError

from adapters.database import DatabaseSession
from entities.plugin_harvest import PluginHarvestState

from .registry import (
    HarvestablePlugin,
    bind_ready_storage,
    dataset_is_ready,
    find_plugin,
    source_identity_of,
    validated_metadata,
)


@contextmanager
def lookup_connection(
    engine: Engine, plugin: HarvestablePlugin, source_identity: str
) -> Iterator[Connection]:
    """Prevent schema replacement during a lookup, then verify the data source.

    ACCESS SHARE permits incremental writes. A rebuild may hold an incompatible
    DDL lock for several minutes; after a short wait, callers can use their
    remote fallback instead. Rechecking state after acquiring table locks keeps
    long-running tasks from reading a later harvest of a different source.
    """
    metadata = validated_metadata(plugin)
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL lock_timeout = '2s'"))
            preparer = connection.dialect.identifier_preparer
            tables = ", ".join(
                preparer.format_table(table)
                for table in sorted(metadata.tables.values(), key=lambda table: table.fullname)
            )
            connection.execute(text(f"LOCK TABLE {tables} IN ACCESS SHARE MODE"))
            row = (
                connection.execute(
                    select(PluginHarvestState.__table__).where(
                        PluginHarvestState.plugin == plugin.name
                    )
                )
                .mappings()
                .one_or_none()
            )
            state = PluginHarvestState(**row) if row is not None else None
            if not dataset_is_ready(plugin, state, source_identity):
                raise HarvestStorageUnavailable(
                    f"Local dataset for {plugin.name!r} no longer matches this plugin"
                )
            yield connection
    except DBAPIError as exc:
        # A schema can disappear between task initialization and this checkout.
        # Do not hide unrelated database failures behind a remote request.
        if getattr(exc.orig, "pgcode", None) in {"42P01", "3F000", "55P03"}:
            raise HarvestStorageUnavailable(
                f"Local dataset for {plugin.name!r} is being rebuilt or is unavailable"
            ) from exc
        raise


def bind_plugin_storage(
    name: str,
    instance: HarvestCapable,
    db_session: DatabaseSession,
    logger: Logger,
) -> bool:
    """Attach compatible local storage once when constructing task plugins."""
    if not instance.needs_harvest:
        return False
    plugin = find_plugin(name)
    if plugin is None or not isinstance(instance, plugin.cls):
        raise ValueError(f"Unregistered harvest plugin {name!r}")
    source_identity = source_identity_of(instance)
    engine = db_session.get_bind().engine
    state = db_session.get(PluginHarvestState, plugin.name)
    ready = bind_ready_storage(
        plugin,
        instance,
        state,
        lambda: lookup_connection(engine, plugin, source_identity),
    )
    if ready:
        logger.info("Using harvested local data for %s", name)
    else:
        logger.info("No compatible harvest for %s; using remote lookup", name)
    return ready

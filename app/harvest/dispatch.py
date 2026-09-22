"""Harvest settings, scheduling and task dispatch.

This layer is deliberately free of HTTP concerns: the beat scheduler and the
worker enqueue harvests too, and neither image ships `service.py` or FastAPI.
`service.py` is the thin API adapter on top of it.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select, text

from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskStatus, TaskType

from .models import PluginHarvestSchedule, PluginHarvestSettings
from .registry import find_plugin, harvestable_plugins
from .schedule import sync_harvest_schedule


class HarvestPluginNotFound(LookupError):
    """No plugin is registered under this name."""


class HarvestEnqueueConflict(RuntimeError):
    """A harvest cannot be queued right now."""


def _settings_with_defaults(
    stored: PluginHarvestSettings | None,
) -> tuple[PluginHarvestSettings, set[str]]:
    """Expose one default preference per discovered plugin.

    Unknown keys are deliberately omitted from returned settings. They are kept
    long enough for schedule reconciliation to remove their old RedBeat entry.
    """

    stored_plugins = stored.plugins if stored else {}
    discovered = {plugin.name for plugin in harvestable_plugins()}
    return (
        PluginHarvestSettings(
            plugins={
                name: stored_plugins.get(name, PluginHarvestSchedule())
                for name in sorted(discovered)
            }
        ),
        set(stored_plugins) - discovered,
    )


def get_harvest_settings(db_session: DatabaseSession) -> PluginHarvestSettings:
    stored = Settings.get(db_session, SettingsScope.PluginHarvest, PluginHarvestSettings)
    settings, _ = _settings_with_defaults(stored)
    return settings


def set_harvest_settings(
    settings: PluginHarvestSettings, db_session: DatabaseSession
) -> PluginHarvestSettings:
    """Persist known preferences and fully reconcile dynamic schedule entries."""

    normalized, stale_names = _settings_with_defaults(settings)
    saved = Settings.upsert(
        db_session,
        SettingsScope.PluginHarvest,
        normalized,
        PluginHarvestSettings,
    )
    sync_harvest_schedule(saved, stale_plugin_names=stale_names)
    return saved


def reconcile_harvest_schedule(db_session: DatabaseSession) -> None:
    stored = Settings.get(db_session, SettingsScope.PluginHarvest, PluginHarvestSettings)
    settings, stale_names = _settings_with_defaults(stored)
    sync_harvest_schedule(settings, stale_plugin_names=stale_names)


def current_task(plugin_name: str, db_session: DatabaseSession) -> Task | None:
    """The Pending or Started harvest task for this plugin, if there is one."""

    candidates = db_session.scalars(
        select(Task)
        .where(
            Task.type == TaskType.HarvestPlugin,
            Task.status.in_([TaskStatus.Pending, TaskStatus.Started]),
        )
        .order_by(Task.created_at.desc())
    ).all()
    return next(
        (task for task in candidates if task.data and task.data.get("plugin") == plugin_name),
        None,
    )


def _enqueue_lock_key(plugin_name: str) -> int:
    digest = hashlib.blake2b(
        f"marc-comparator:harvest-enqueue:{plugin_name}".encode(), digest_size=8
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


async def enqueue_harvest(
    plugin_name: str,
    created_by: str,
    db_session: DatabaseSession,
    *,
    full_rebuild: bool = False,
    scheduled: bool = False,
) -> TaskSchema:
    """Create one managed task per plugin, reusing an already active one.

    This short advisory lock protects the enqueue check-and-insert sequence.
    The long-running data transaction takes a distinct lock in the worker.
    """

    if find_plugin(plugin_name) is None:
        raise HarvestPluginNotFound(f"Unknown harvest plugin '{plugin_name}'.")
    if scheduled:
        schedule = get_harvest_settings(db_session).plugins[plugin_name]
        if not schedule.enabled:
            raise HarvestEnqueueConflict(
                f"Scheduled harvesting is disabled for plugin '{plugin_name}'."
            )

    acquired = db_session.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
        {"lock_key": _enqueue_lock_key(plugin_name)},
    ).scalar_one()
    if not acquired:
        active = current_task(plugin_name, db_session)
        if active is not None:
            return TaskSchema.model_validate(active, from_attributes=True)
        raise HarvestEnqueueConflict(f"A harvest task for plugin '{plugin_name}' is being queued.")

    active = current_task(plugin_name, db_session)
    if active is not None:
        db_session.commit()  # releases the transaction-scoped enqueue lock
        return TaskSchema.model_validate(active, from_attributes=True)

    task = Task(
        name=("Scheduled " if scheduled else "") + f"harvest for plugin {plugin_name}",
        type=TaskType.HarvestPlugin,
        data={"plugin": plugin_name, "full_rebuild": full_rebuild, "scheduled": scheduled},
        created_by=created_by,
    )
    return await enqueue_task(task, db_session)

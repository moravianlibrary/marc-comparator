"""Operator-facing harvest status and the API's error translation.

Scheduling, settings and enqueueing live in `dispatch`, which the worker and
beat images also need; this module is API-only and is stripped from them.
"""

from __future__ import annotations

from contextlib import suppress

from fastapi import HTTPException, status

from adapters.database import DatabaseSession
from entities.plugin_harvest import PluginHarvestState
from entities.task import TaskSchema

from .dispatch import (
    HarvestEnqueueConflict,
    HarvestPluginNotFound,
    current_task,
    get_harvest_settings,
)
from .dispatch import enqueue_harvest as dispatch_harvest
from .models import HarvestPluginStatus
from .registry import dataset_is_ready, harvestable_plugins, instantiate, source_identity_of


def list_plugins(db_session: DatabaseSession) -> list[HarvestPluginStatus]:
    settings = get_harvest_settings(db_session)
    statuses: list[HarvestPluginStatus] = []
    for plugin in harvestable_plugins():
        state = db_session.get(PluginHarvestState, plugin.name)
        source_identity: str | None = None
        with suppress(Exception):
            source_identity = source_identity_of(instantiate(plugin, db_session))
        compatible = bool(source_identity and dataset_is_ready(plugin, state, source_identity))
        schedule = settings.plugins[plugin.name]
        task = current_task(plugin.name, db_session)
        statuses.append(
            HarvestPluginStatus(
                name=plugin.name,
                scope=plugin.scope.value,
                enabled=schedule.enabled,
                cron=schedule.cron,
                ready=compatible,
                schema_version=plugin.schema_version,
                source_identity=source_identity,
                state_source_identity=state.source_identity if state else None,
                compatible=compatible,
                watermark=state.watermark if state else None,
                records=state.records if state else None,
                last_harvest_at=state.last_harvest_at if state else None,
                current_task=(
                    TaskSchema.model_validate(task, from_attributes=True) if task else None
                ),
            )
        )
    return statuses


async def enqueue_harvest(
    plugin_name: str,
    created_by: str,
    db_session: DatabaseSession,
    *,
    full_rebuild: bool = False,
) -> TaskSchema:
    try:
        return await dispatch_harvest(
            plugin_name, created_by, db_session, full_rebuild=full_rebuild
        )
    except HarvestPluginNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except HarvestEnqueueConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

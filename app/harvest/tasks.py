"""Worker implementation for a single plugin harvest."""

from __future__ import annotations

from time import monotonic

from marc_comparator.harvest import HarvestContext
from sqlalchemy import select

from adapters.database import SessionLocal, get_db_session
from adapters.tasks import ManagedTask
from entities.plugin_harvest import PluginHarvestState
from entities.task import Task, TaskStatus

from .dispatch import get_harvest_settings
from .registry import (
    HarvestAlreadyRunningError,
    acquire_harvest_lock,
    complete_harvest,
    ensure_schema,
    find_plugin,
    instantiate,
    source_identity_of,
)

#: How often the task row is committed so a long harvest stays observable.
#: Progress is written into the task session but stays invisible to everyone
#: else until that session commits, and the harvest itself only commits once,
#: at the end — without this a multi-minute run would sit at 0%.
PROGRESS_COMMIT_SECONDS = 5.0


class HarvestCancelledError(RuntimeError):
    """Raised before publication when an operator revokes this managed task."""


def _assert_not_revoked(task_id: str) -> None:
    """Read cancellation through an independent task/progress session.

    The harvest transaction deliberately cannot see task/progress commits until
    it ends. A separate session also avoids committing harvested rows when
    ManagedTask saves progress or trace output.
    """

    with get_db_session() as task_session:
        task_status = task_session.scalar(select(Task.status).where(Task.task_id == task_id))
    if task_status == TaskStatus.Revoked:
        raise HarvestCancelledError(f"Harvest task {task_id} was revoked")


async def harvest_plugin(task_id: str) -> None:
    """Run one plugin inside its own atomic data transaction."""

    async with ManagedTask(task_id=task_id) as ctx:
        data = ctx.task.data or {}
        plugin_name = data.get("plugin")
        if not isinstance(plugin_name, str):
            raise ValueError("Harvest task has no plugin name")
        full_rebuild = data.get("full_rebuild", False)
        scheduled = data.get("scheduled", False)
        if not isinstance(full_rebuild, bool) or not isinstance(scheduled, bool):
            raise ValueError("Harvest task has invalid input")

        plugin = find_plugin(plugin_name)
        if plugin is None:
            raise ValueError(f"Harvest plugin {plugin_name!r} is no longer available")
        if scheduled and not get_harvest_settings(ctx.db_session).plugins[plugin_name].enabled:
            ctx.logger.info("Scheduled harvest is disabled; skipping this queued run.")
            return

        data_session = SessionLocal()
        try:
            with data_session.begin():
                try:
                    acquire_harvest_lock(plugin, data_session)
                except HarvestAlreadyRunningError:
                    # The enqueue lock normally prevents this. The data lock is
                    # still authoritative when separate workers race or Redis is
                    # unavailable, and makes this duplicate task a harmless no-op.
                    ctx.logger.info("Another harvest holds the database lock; skipping duplicate.")
                    return

                instance = instantiate(plugin, data_session)
                source_identity = source_identity_of(instance)
                rebuilt = ensure_schema(
                    plugin,
                    data_session,
                    source_identity,
                    force=full_rebuild,
                )
                state = data_session.get(PluginHarvestState, plugin.name)
                if state is None:
                    raise RuntimeError(f"Harvest state missing for plugin {plugin.name!r}")
                if rebuilt:
                    ctx.logger.info("Created a new local dataset; fetching the full source.")
                elif state.watermark is None:
                    ctx.logger.info("No watermark is available; fetching the full source.")
                else:
                    ctx.logger.info("Fetching changes since the prior successful watermark.")

                last_published = monotonic()

                def progress(done: int, total: int | None = None) -> None:
                    nonlocal last_published
                    if done < 0 or total is not None and total < done:
                        raise ValueError(
                            "Harvest progress must be non-negative and not exceed its total"
                        )
                    _assert_not_revoked(task_id)
                    ctx.progress = done
                    ctx.total = total
                    if total is None:
                        # Assigning the total is what normally writes the row.
                        # With an unknown total nothing would be written at all,
                        # including the heartbeat the orphan reaper watches.
                        ctx.update_progress()
                    now = monotonic()
                    if now - last_published >= PROGRESS_COMMIT_SECONDS:
                        # The task session is separate from the harvest
                        # transaction, so this publishes progress and log output
                        # without committing a single harvested row.
                        ctx.db_session.commit()
                        last_published = now

                result = await instance.harvest(
                    HarvestContext(
                        connection=data_session.connection(),
                        schema=plugin.schema_name,
                        progress=progress,
                        watermark=state.watermark,
                    )
                )
                # A final fresh check closes the cancellation window after the
                # plugin's final progress update and before the data commit.
                _assert_not_revoked(task_id)
                complete_harvest(plugin, data_session, result, source_identity)

            ctx.logger.info(f"Harvest completed: {result.records} records published.")
        finally:
            data_session.close()

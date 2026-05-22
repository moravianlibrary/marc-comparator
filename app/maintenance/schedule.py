import logging

from celery.schedules import schedule
from redbeat import RedBeatSchedulerEntry

from adapters.tasks import tasks_client
from maintenance.models import MaintenanceSettings

logger = logging.getLogger(__name__)

TASK_CLEANUP_ENTRY = "redbeat:periodic-task-cleanup"
SECTOR_COMPACTION_ENTRY = "redbeat:periodic-sector-compaction"


def sync_redbeat_schedule(settings: MaintenanceSettings) -> None:
    """
    Create, update, or delete redbeat schedule entries based on maintenance settings.
    Called whenever admin saves maintenance settings via the API.
    """
    _sync_entry(
        name=TASK_CLEANUP_ENTRY,
        task_name="periodic_task_cleanup",
        enabled=settings.task_cleanup.enabled,
        interval_hours=settings.task_cleanup.interval_hours,
        args=[settings.task_cleanup_max_age_days],
    )
    _sync_entry(
        name=SECTOR_COMPACTION_ENTRY,
        task_name="periodic_sector_compaction",
        enabled=settings.sector_compaction.enabled,
        interval_hours=settings.sector_compaction.interval_hours,
    )


def _sync_entry(
    name: str,
    task_name: str,
    enabled: bool,
    interval_hours: int,
    args: list | None = None,
) -> None:
    """Create/update a redbeat entry if enabled, delete it if disabled."""
    if enabled:
        interval_seconds = interval_hours * 3600
        entry = RedBeatSchedulerEntry(
            name=name,
            task=task_name,
            schedule=schedule(run_every=interval_seconds),
            args=args or [],
            app=tasks_client,
        )
        entry.save()
        logger.info(f"Redbeat schedule '{name}' set to every {interval_hours}h")
    else:
        try:
            entry = RedBeatSchedulerEntry.from_key(name, app=tasks_client)
            entry.delete()
            logger.info(f"Redbeat schedule '{name}' removed (disabled)")
        except KeyError:
            pass

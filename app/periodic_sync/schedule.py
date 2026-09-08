import logging

from celery.schedules import schedule
from redbeat import RedBeatSchedulerEntry

from adapters.tasks import tasks_client

from .models import PeriodicSyncSettings

logger = logging.getLogger(__name__)

ENTRY_PREFIX = "redbeat:periodic-sync-"


def entry_name(base: str) -> str:
    return f"{ENTRY_PREFIX}{base}"


def sync_periodic_sync_schedule(settings: PeriodicSyncSettings) -> None:
    """Reconcile one redbeat entry per configured base.

    An enabled base gets/updates ``redbeat:periodic-sync-{base}`` running
    ``periodic_sync_records`` with the base as its argument; a disabled base
    has its entry removed. Called on periodic-sync settings save and on startup.
    """
    for base_config in settings.bases:
        name = entry_name(base_config.base)
        if base_config.enabled:
            entry = RedBeatSchedulerEntry(
                name=name,
                task="periodic_sync_records",
                schedule=schedule(run_every=base_config.interval_hours * 3600),
                args=[base_config.base],
                app=tasks_client,
            )
            entry.save()
            logger.info(f"Periodic sync '{name}' set to every {base_config.interval_hours}h")
        else:
            try:
                RedBeatSchedulerEntry.from_key(name, app=tasks_client).delete()
                logger.info(f"Periodic sync '{name}' removed (disabled)")
            except KeyError:
                pass

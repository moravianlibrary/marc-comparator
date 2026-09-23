from adapters.redbeat_schedule import sync_entry

from .models import PeriodicSyncSettings

ENTRY_PREFIX = "redbeat:periodic-sync-"
PROCESSING_ENTRY = "redbeat:periodic-process-records"


def entry_name(base: str) -> str:
    return f"{ENTRY_PREFIX}{base}"


def sync_periodic_sync_schedule(settings: PeriodicSyncSettings) -> None:
    """Reconcile one redbeat entry per configured base, plus the processing entry.

    An enabled base gets/updates ``redbeat:periodic-sync-{base}`` running
    ``periodic_sync_records`` with the base as its argument; a disabled base has
    its entry removed. Processing is not per-base — it runs over whatever is
    unprocessed — so it gets a single entry reconciled alongside them. Called on
    periodic-sync settings save and on startup.
    """
    for base_config in settings.bases:
        sync_entry(
            name=entry_name(base_config.base),
            task_name="periodic_sync_records",
            enabled=base_config.enabled,
            cron=base_config.cron,
            args=[base_config.base],
        )

    sync_entry(
        name=PROCESSING_ENTRY,
        task_name="periodic_process_records",
        enabled=settings.processing.enabled,
        cron=settings.processing.cron,
    )

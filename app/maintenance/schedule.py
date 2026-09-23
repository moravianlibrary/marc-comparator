from adapters.redbeat_schedule import sync_entry
from maintenance.models import MaintenanceSettings

TASK_CLEANUP_ENTRY = "redbeat:periodic-task-cleanup"
SECTOR_COMPACTION_ENTRY = "redbeat:periodic-sector-compaction"
ORPHAN_REAPER_ENTRY = "redbeat:reap-orphaned-tasks"


def sync_redbeat_schedule(settings: MaintenanceSettings) -> None:
    """
    Create, update, or delete redbeat schedule entries based on maintenance settings.
    Called whenever admin saves maintenance settings via the API, and on startup.
    """
    sync_entry(
        name=TASK_CLEANUP_ENTRY,
        task_name="periodic_task_cleanup",
        enabled=settings.task_cleanup.enabled,
        cron=settings.task_cleanup.cron,
        args=[settings.task_cleanup_max_age_days],
    )
    sync_entry(
        name=SECTOR_COMPACTION_ENTRY,
        task_name="periodic_sector_compaction",
        enabled=settings.sector_compaction.enabled,
        cron=settings.sector_compaction.cron,
    )
    sync_entry(
        name=ORPHAN_REAPER_ENTRY,
        task_name="reap_orphaned_tasks",
        enabled=settings.orphan_reaper.enabled,
        cron=settings.orphan_reaper.cron,
    )

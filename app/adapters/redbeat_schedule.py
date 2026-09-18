import logging

from celery.schedules import schedule
from redbeat import RedBeatSchedulerEntry

from adapters.tasks import tasks_client

logger = logging.getLogger(__name__)


def sync_entry(
    name: str,
    task_name: str,
    enabled: bool,
    interval_hours: int,
    args: list | None = None,
) -> None:
    """Create/update a redbeat entry if enabled, delete it if disabled."""
    entry = RedBeatSchedulerEntry(
        name=name,
        task=task_name,
        schedule=schedule(run_every=interval_hours * 3600),
        args=args or [],
        app=tasks_client,
    )

    if enabled:
        entry.save()
        logger.info(f"Redbeat schedule '{name}' set to every {interval_hours}h")
        return

    # Delete through the entry rather than RedBeatSchedulerEntry.from_key(name).
    # redbeat stores an entry under `key_prefix + name`, so handing from_key the
    # bare name looks up a key that never exists: it raises KeyError and the
    # removal is silently skipped, leaving a disabled job still scheduled.
    # An entry object knows its own key, and deleting a missing one is a no-op.
    entry.delete()
    logger.info(f"Redbeat schedule '{name}' not scheduled (disabled)")

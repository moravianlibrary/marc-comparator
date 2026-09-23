import logging

from redbeat import RedBeatSchedulerEntry

from adapters.cron import parse_cron
from adapters.tasks import tasks_client

logger = logging.getLogger(__name__)


def sync_entry(
    name: str,
    task_name: str,
    enabled: bool,
    cron: str,
    args: list | None = None,
) -> None:
    """Create/update a redbeat entry if enabled, delete it if disabled."""
    entry = RedBeatSchedulerEntry(
        name=name,
        task=task_name,
        schedule=parse_cron(cron),
        args=args or [],
        app=tasks_client,
    )

    if enabled:
        entry.save()
        logger.info(f"Redbeat schedule '{name}' set to cron '{cron}'")
        return

    # Delete through the entry rather than RedBeatSchedulerEntry.from_key(name).
    # redbeat stores an entry under `key_prefix + name`, so handing from_key the
    # bare name looks up a key that never exists: it raises KeyError and the
    # removal is silently skipped, leaving a disabled job still scheduled.
    # An entry object knows its own key, and deleting a missing one is a no-op.
    entry.delete()
    logger.info(f"Redbeat schedule '{name}' not scheduled (disabled)")

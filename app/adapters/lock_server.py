import logging
import threading
from contextlib import contextmanager
from typing import List

from redis import Redis
from redis.lock import Lock

from config import config

logger = logging.getLogger(__name__)

lock_server_client = Redis(
    host=config.broker.host, port=config.broker.port, db=config.broker.db
)

ACTIVE_LOCKS_KEY = "active_locks"


@contextmanager
def one_at_a_time_lock(
    lock_name: str,
    blocking: bool = True,
    blocking_timeout: int = 30,
    timeout: int = 60,
):
    """
    Context manager to ensure only one instance of a task runs at a time,
    using a Redis-based distributed lock.

    Parameters
    ----------
    lock_name : str
        The unique name of the lock.
    blocking : bool, optional
        Whether the call should block until the lock is acquired.
        Default is True.
    blocking_timeout : int, optional
        Maximum number of seconds to wait to acquire the lock if
        `blocking` is True. Default is 30.
    timeout : int, optional
        TTL in seconds for the lock key. If the holder crashes, the lock
        auto-releases after this period. Default is 60.

    Yields
    ------
    Lock | None
        The Lock object if acquired (truthy), None if not (falsy).
        Callers can use `if lock:` to check.
        A background watchdog thread auto-renews the TTL while the
        context is open, so callers do not need to call reacquire().
    """
    lock = Lock(lock_server_client, name=lock_name, timeout=timeout)

    acquired = lock.acquire(
        blocking=blocking, blocking_timeout=blocking_timeout
    )
    if acquired:
        lock_server_client.sadd(ACTIVE_LOCKS_KEY, lock_name)
        _publish_lock_acquired(lock_name)
        stop_event = threading.Event()
        watchdog = threading.Thread(
            target=_renewal_watchdog,
            args=(lock, lock_name, timeout, stop_event),
            daemon=True,
        )
        watchdog.start()
        try:
            yield lock
        finally:
            stop_event.set()
            watchdog.join(timeout=5)
            try:
                lock.release()
            except Exception:
                logger.warning(f"Failed to release lock '{lock_name}'", exc_info=True)
            lock_server_client.srem(ACTIVE_LOCKS_KEY, lock_name)
            _publish_lock_released(lock_name)
    else:
        yield None


def _renewal_watchdog(
    lock: Lock, lock_name: str, timeout: int, stop_event: threading.Event
) -> None:
    """Background thread that extends the lock TTL every timeout/3 seconds."""
    interval = max(timeout // 3, 1)
    while not stop_event.wait(interval):
        try:
            lock.reacquire()
        except Exception:
            logger.warning(f"Lock renewal failed for '{lock_name}'", exc_info=True)
            return


def get_active_locks() -> List[str]:
    """Return the list of currently held locks, cleaning up stale entries."""
    members = lock_server_client.smembers(ACTIVE_LOCKS_KEY)
    active = []
    stale = []

    for name in members:
        # Lock keys in redis-py are stored under the lock_name directly
        if lock_server_client.exists(name):
            active.append(name if isinstance(name, str) else name.decode())
        else:
            stale.append(name)

    if stale:
        lock_server_client.srem(ACTIVE_LOCKS_KEY, *stale)

    return active


def _publish_lock_acquired(lock_name: str) -> None:
    try:
        from adapters.events import LockAcquiredEvent, publish_event
        publish_event(LockAcquiredEvent(lock_name=lock_name))
    except Exception:
        logger.warning("Failed to publish lock acquired event", exc_info=True)


def _publish_lock_released(lock_name: str) -> None:
    try:
        from adapters.events import LockReleasedEvent, publish_event
        publish_event(LockReleasedEvent(lock_name=lock_name))
    except Exception:
        logger.warning("Failed to publish lock released event", exc_info=True)

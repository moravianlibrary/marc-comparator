from contextlib import contextmanager

from redis import Redis
from redis.lock import Lock

from config import config

lock_server_client = Redis(
    host=config.broker.host, port=config.broker.port, db=config.broker.db
)


@contextmanager
def one_at_a_time_lock(
    lock_name: str,
    blocking: bool = True,
    blocking_timeout: int = 30,
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
        Maximum number of seconds to wait
        to acquire the lock if `blocking` is True.
        If the lock cannot be acquired in this time,
        the context will yield False.
        Default is 30.

    Yields
    ------
    bool
        True if the lock was successfully acquired and the block can proceed.
        False if the lock could not be acquired (e.g., it is already held).

    Examples
    --------
    >>> with one_at_a_time_lock("long-task-lock") as acquired:
    ...     if not acquired:
    ...         print("Another instance is running. Exiting.")
    ...     else:
    ...         do_long_running_task()
    """
    lock = Lock(lock_server_client, name=lock_name)

    acquired = lock.acquire(
        blocking=blocking, blocking_timeout=blocking_timeout
    )
    if acquired:
        try:
            yield True
        finally:
            lock.release()
    else:
        yield False

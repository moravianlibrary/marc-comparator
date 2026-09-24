import time

from redis.lock import Lock

from adapters.lock_server import get_active_locks, one_at_a_time_lock


class TestLockTTL:
    def test_lock_yields_lock_object_on_success(self, lock_server_client):
        with one_at_a_time_lock("test-ttl-lock") as lock:
            assert lock is not None

    def test_lock_yields_none_on_failure(self, lock_server_client):
        with one_at_a_time_lock("test-contention") as lock1:
            assert lock1 is not None
            with one_at_a_time_lock("test-contention", blocking=False) as lock2:
                assert lock2 is None

    def test_lock_auto_releases_after_ttl(self, lock_server_client):
        # A holder that died leaves no watchdog behind, so the TTL is the only
        # thing that frees the lock. Held directly rather than through the
        # context manager, which renews for as long as its body runs.
        abandoned = Lock(lock_server_client, name="test-ttl-expire", timeout=1)
        assert abandoned.acquire(blocking=False)
        time.sleep(1.5)

        with one_at_a_time_lock("test-ttl-expire", blocking=False) as lock:
            assert lock is not None

    def test_lock_is_renewed_past_its_timeout(self, lock_server_client):
        """The watchdog renews from its own thread, where the token is not.

        redis-py keeps the lock token in thread-local storage by default, so a
        watchdog thread saw no token and reacquire() failed with AttributeError
        on its first tick — silently, then never again, because the thread gave
        up on the first error. The lock expired a timeout later while the task
        went on running for hours believing it was the only one.
        """

        with one_at_a_time_lock("test-renewal", timeout=3) as lock:
            assert lock is not None
            # Two renewal ticks (timeout // 3) and well past the original TTL.
            time.sleep(4)
            assert lock_server_client.ttl("test-renewal") > 0
            assert lock.locked()

        assert lock_server_client.exists("test-renewal") == 0

    def test_lock_reacquire_extends_ttl(self, lock_server_client):
        with one_at_a_time_lock("test-reacquire", timeout=2) as lock:
            assert lock is not None
            time.sleep(1)
            lock.reacquire()
            time.sleep(1.5)
            # Lock should still be held because we reacquired
            assert lock.locked()


class TestActiveLockTracking:
    def test_active_lock_added_on_acquire(self, lock_server_client):
        with one_at_a_time_lock("test-active") as lock:
            assert lock is not None
            active = get_active_locks()
            assert "test-active" in active

    def test_active_lock_removed_on_release(self, lock_server_client):
        with one_at_a_time_lock("test-release") as lock:
            assert lock is not None
        active = get_active_locks()
        assert "test-release" not in active

    def test_stale_active_lock_cleaned_on_read(self, lock_server_client):
        from adapters.lock_server import ACTIVE_LOCKS_KEY
        from adapters.lock_server import lock_server_client as client

        client.sadd(ACTIVE_LOCKS_KEY, "stale-lock")

        active = get_active_locks()
        assert "stale-lock" not in active

    def test_failed_acquire_does_not_add_to_active(self, lock_server_client):
        with one_at_a_time_lock("test-no-add") as lock1:
            assert lock1 is not None
            with one_at_a_time_lock("test-no-add", blocking=False) as lock2:
                assert lock2 is None
            # Only one entry, not two
            active = get_active_locks()
            assert "test-no-add" in active
        active = get_active_locks()
        assert "test-no-add" not in active

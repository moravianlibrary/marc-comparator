import time

import pytest

from adapters.lock_server import get_active_locks, one_at_a_time_lock


class TestLockTTL:
    def test_lock_yields_lock_object_on_success(self, lock_server_client):
        with one_at_a_time_lock("test-ttl-lock") as lock:
            assert lock is not None

    def test_lock_yields_none_on_failure(self, lock_server_client):
        with one_at_a_time_lock("test-contention") as lock1:
            assert lock1 is not None
            with one_at_a_time_lock(
                "test-contention", blocking=False
            ) as lock2:
                assert lock2 is None

    def test_lock_auto_releases_after_ttl(self, lock_server_client):
        with one_at_a_time_lock("test-ttl-expire", timeout=1) as lock:
            assert lock is not None
            time.sleep(1.5)

        # Lock should have expired -- can re-acquire immediately
        with one_at_a_time_lock(
            "test-ttl-expire", blocking=False
        ) as lock:
            assert lock is not None

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
        from adapters.lock_server import ACTIVE_LOCKS_KEY, lock_server_client as client
        client.sadd(ACTIVE_LOCKS_KEY, "stale-lock")

        active = get_active_locks()
        assert "stale-lock" not in active

    def test_failed_acquire_does_not_add_to_active(self, lock_server_client):
        with one_at_a_time_lock("test-no-add") as lock1:
            assert lock1 is not None
            with one_at_a_time_lock(
                "test-no-add", blocking=False
            ) as lock2:
                assert lock2 is None
            # Only one entry, not two
            active = get_active_locks()
            assert "test-no-add" in active
        active = get_active_locks()
        assert "test-no-add" not in active

from unittest.mock import patch

import pytest

from adapters.marc_sectors import (
    CACHE_PREFIX,
    read_marc,
    upsert_record_in_sector,
)


@pytest.mark.db
@pytest.mark.redis
class TestMarcCache:
    def test_read_marc_caches_result(self, db_session, marc_cache_client):
        """First read should cache, second read should hit cache (no DB)."""
        base = "MZK01"
        sysno = "000000001"
        marc_bytes = b"\x00\x01\x02test-marc-data"

        upsert_record_in_sector(db_session, base, sysno, marc_bytes)
        db_session.commit()

        # First read — should populate cache
        result1 = read_marc(db_session, base, sysno)
        assert result1 == marc_bytes

        # Verify cache key exists
        cache_key = f"{CACHE_PREFIX}{base}:{sysno}"
        cached = marc_cache_client.get(cache_key)
        assert cached == marc_bytes

        # Second read with no DB — should hit cache
        with patch("adapters.marc_sectors.MarcRecordIndex") as mock_idx:
            result2 = read_marc(db_session, base, sysno)
            assert result2 == marc_bytes
            mock_idx.assert_not_called()

    def test_upsert_invalidates_cache(self, db_session, marc_cache_client):
        """Writing a record should invalidate its cache entry."""
        base = "MZK01"
        sysno = "000000001"
        marc_v1 = b"\x00\x01original"
        marc_v2 = b"\x00\x01updated"

        upsert_record_in_sector(db_session, base, sysno, marc_v1)
        db_session.commit()

        # Populate cache
        result1 = read_marc(db_session, base, sysno)
        assert result1 == marc_v1

        # Update record — should invalidate cache
        upsert_record_in_sector(db_session, base, sysno, marc_v2)
        db_session.commit()

        # Read again — should get new data
        result2 = read_marc(db_session, base, sysno)
        assert result2 == marc_v2

    def test_read_marc_no_record_returns_none_not_cached(self, db_session, marc_cache_client):
        """None results should not be cached."""
        result = read_marc(db_session, "MZK01", "999999999")
        assert result is None

        cache_key = f"{CACHE_PREFIX}MZK01:999999999"
        assert marc_cache_client.get(cache_key) is None

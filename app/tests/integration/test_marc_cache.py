from unittest.mock import patch

import pytest

from adapters.marc_sectors import (
    CACHE_PREFIX,
    _decompressor,
    read_marc,
    read_marc_many,
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


class CountingDecompressor:
    """Stands in for the zstd decompressor, whose methods are read-only."""

    def __init__(self) -> None:
        self.calls = 0

    def decompress(self, data: bytes) -> bytes:
        self.calls += 1
        return _decompressor.decompress(data)


@pytest.mark.db
@pytest.mark.redis
class TestBatchedRead:
    """Reading many records at once must answer exactly as reading them singly."""

    BASE = "MZK02"
    RECORDS = {
        "000000001": b"first-record",
        "000000002": b"second-record",
        "000002500": b"far-away-record",
    }

    def store(self, db_session):
        for system_number, marc in self.RECORDS.items():
            upsert_record_in_sector(db_session, self.BASE, system_number, marc)
        db_session.commit()

    def test_returns_what_reading_one_at_a_time_returns(self, db_session, marc_cache_client):
        self.store(db_session)
        wanted = [*self.RECORDS, "000009999"]

        singly = {
            system_number: marc
            for system_number in wanted
            if (marc := read_marc(db_session, self.BASE, system_number)) is not None
        }
        marc_cache_client.flushdb()
        together = read_marc_many(db_session, self.BASE, wanted)

        assert together == singly
        # A record storage does not hold is absent, not None, as for read_marc.
        assert "000009999" not in together

    def test_a_sector_is_decompressed_once_for_all_its_records(self, db_session, marc_cache_client):
        self.store(db_session)
        marc_cache_client.flushdb()

        counter = CountingDecompressor()
        with patch("adapters.marc_sectors._decompressor", counter):
            read_marc_many(db_session, self.BASE, list(self.RECORDS))

        # Two records share a sector, the third is far enough away to have
        # its own — so three records cost two decompressions, not three.
        assert counter.calls == 2

    def test_what_is_cached_is_not_read_again(self, db_session, marc_cache_client):
        self.store(db_session)
        marc_cache_client.flushdb()
        read_marc(db_session, self.BASE, "000000001")

        counter = CountingDecompressor()
        with patch("adapters.marc_sectors._decompressor", counter):
            found = read_marc_many(db_session, self.BASE, ["000000001"])

        assert found == {"000000001": self.RECORDS["000000001"]}
        assert counter.calls == 0

    def test_asking_for_nothing_reads_nothing(self, db_session):
        assert read_marc_many(db_session, self.BASE, []) == {}

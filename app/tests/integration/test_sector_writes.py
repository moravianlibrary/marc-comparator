from unittest.mock import patch

import pytest
from sqlalchemy import event

from adapters.marc_sectors import (
    CACHE_PREFIX,
    SectorBuffer,
    read_marc,
    upsert_record_in_sector,
)


class _CountSelects:
    """Counts the SELECTs issued against one table while it is active.

    Writes are not counted: the batching is about how many round trips it takes
    to find out which index rows already exist, not about how they are written.
    """

    def __init__(self, db_session, table: str):
        self._bind = db_session.get_bind()
        self._table = table
        self.statements: list[str] = []

    @property
    def count(self) -> int:
        return len(self.statements)

    def __enter__(self):
        event.listen(self._bind, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *_):
        event.remove(self._bind, "before_cursor_execute", self._on_execute)
        return False

    def _on_execute(self, _conn, _cursor, statement, *_args):
        collapsed = " ".join(statement.split()).lower()
        if collapsed.startswith("select") and self._table in collapsed:
            self.statements.append(collapsed[:120])


@pytest.mark.db
@pytest.mark.redis
class TestUnchangedRecordsAreNotRewritten:
    def test_upsert_of_identical_bytes_does_not_rewrite(self, db_session, marc_cache_client):
        """Re-storing a record byte for byte should not touch its sector."""
        base, sysno = "MZK01", "000000001"
        marc = b"\x00\x01original"

        upsert_record_in_sector(db_session, base, sysno, marc)
        db_session.commit()

        # A read populates the cache; a sector rewrite would invalidate it.
        assert read_marc(db_session, base, sysno) == marc
        assert marc_cache_client.get(f"{CACHE_PREFIX}{base}:{sysno}") == marc

        with patch("adapters.marc_sectors.write_records_to_sector") as write:
            upsert_record_in_sector(db_session, base, sysno, marc)
            write.assert_not_called()

        assert marc_cache_client.get(f"{CACHE_PREFIX}{base}:{sysno}") == marc

    def test_upsert_of_different_bytes_still_rewrites(self, db_session, marc_cache_client):
        """The skip must not swallow a real change."""
        base, sysno = "MZK01", "000000002"

        upsert_record_in_sector(db_session, base, sysno, b"\x00\x01original")
        db_session.commit()
        assert read_marc(db_session, base, sysno) == b"\x00\x01original"

        upsert_record_in_sector(db_session, base, sysno, b"\x00\x01updated")
        db_session.commit()

        assert read_marc(db_session, base, sysno) == b"\x00\x01updated"

    def test_buffer_flush_skips_a_sector_that_would_not_change(self, db_session, marc_cache_client):
        """Linking re-stores the same authority record repeatedly; that must be free."""
        base = "AUT10"
        records = {"000001000": b"authority-a", "000001001": b"authority-b"}

        buffer = SectorBuffer(lambda: db_session)
        for sysno, marc in records.items():
            buffer.add(base, sysno, marc)
        buffer.flush_all()
        db_session.commit()

        for sysno, marc in records.items():
            assert read_marc(db_session, base, sysno) == marc

        # Exactly what the linker does on the next catalogue record pointing here.
        for sysno, marc in records.items():
            buffer.add(base, sysno, marc)

        with patch("adapters.marc_sectors.write_records_to_sector") as write:
            buffer.flush_all()
            write.assert_not_called()

        # The buffer is still drained, and the records still read back.
        assert not any(buffer.holds(base, sysno) for sysno in records)
        for sysno, marc in records.items():
            assert read_marc(db_session, base, sysno) == marc

    def test_buffer_flush_writes_when_one_record_differs(self, db_session, marc_cache_client):
        """One changed record in the buffer is enough to earn the write."""
        base = "AUT11"
        buffer = SectorBuffer(lambda: db_session)
        buffer.add(base, "000002000", b"unchanged")
        buffer.add(base, "000002001", b"before")
        buffer.flush_all()
        db_session.commit()

        buffer.add(base, "000002000", b"unchanged")
        buffer.add(base, "000002001", b"after")
        buffer.flush_all()
        db_session.commit()

        assert read_marc(db_session, base, "000002000") == b"unchanged"
        assert read_marc(db_session, base, "000002001") == b"after"


@pytest.mark.db
class TestSectorIndexLookupIsBatched:
    def test_index_rows_are_fetched_in_one_query(self, db_session):
        """Writing a sector must not cost a SELECT per record in it."""
        base = "MZK02"
        records = {f"00000{3000 + i}": f"record-{i}".encode() for i in range(25)}

        buffer = SectorBuffer(lambda: db_session)
        for sysno, marc in records.items():
            buffer.add(base, sysno, marc)
        buffer.flush_all()
        db_session.commit()

        # Rewrite the whole sector with changed content, so every index row is
        # looked up and updated.
        for sysno in records:
            buffer.add(base, sysno, b"changed-" + sysno.encode())

        with _CountSelects(db_session, "marc_record_index") as counted:
            buffer.flush_all()
            db_session.flush()

        # One to rebuild the sector from the index, one to load the rows being
        # updated. A per-record lookup would be 25.
        assert counted.count <= 2, (
            f"{counted.count} SELECTs against marc_record_index for "
            f"{len(records)} records — the lookups are not batched:\n"
            + "\n".join(counted.statements)
        )

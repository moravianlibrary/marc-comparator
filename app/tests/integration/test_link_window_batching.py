"""The linking window reads its records in batches, not one at a time.

Read per record, a window of 200 costs 200 identity lookups plus two more
queries each to find and decompress the MARC. The records in a window are
consecutive system numbers and so share very few sectors, which is what makes
the batched read so much cheaper than the sum of its parts.
"""

import logging

import pytest
from sqlalchemy import event

from adapters.database import DatabaseSession
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from tests.conftest import create_catalog_record, load_test_record

WINDOW = 12


class _CountSelects:
    """Counts SELECTs issued while it is active."""

    def __init__(self, db_session: DatabaseSession):
        self._bind = db_session.get_bind()
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
        if collapsed.startswith("select"):
            self.statements.append(collapsed[:140])


@pytest.fixture
def window_records(db_session: DatabaseSession, marc_cache_client) -> list[str]:
    """A window of records sharing one sector, as a real window would."""
    marc_record = load_test_record("MZK01-001217709.mrc")
    ids = []
    for offset in range(WINDOW):
        record = create_catalog_record(db_session, "MZK01", f"00090{offset:04d}", marc_record)
        ids.append(record.id)
    db_session.commit()
    # A window read after a write must not be served from a cache the write
    # populated, or the test measures nothing.
    marc_cache_client.flushdb()
    return ids


@pytest.mark.db
@pytest.mark.redis
class TestTheWindowIsReadInBatches:
    @pytest.mark.asyncio
    async def test_a_window_costs_a_handful_of_queries(self, db_session, window_records):
        from authority_linking.tasks import announce_link_window

        with _CountSelects(db_session) as counted:
            marc_by_id = await announce_link_window(
                db_session, window_records, ["SKC"], [], logging.getLogger("t")
            )

        assert set(marc_by_id) == set(window_records), "every record must come back parsed"
        # Identity/base/system number, the index rows, and the one sector they
        # share. Per record it would be three times WINDOW.
        assert counted.count <= 4, (
            f"{counted.count} SELECTs for {WINDOW} records — the window is not batched:\n"
            + "\n".join(counted.statements)
        )

    @pytest.mark.asyncio
    async def test_a_record_without_marc_is_skipped_not_fatal(self, db_session, window_records):
        """A window is a hint; one record's missing MARC must not lose the batch."""
        from authority_linking.tasks import announce_link_window

        orphan = CatalogRecord(base="MZK01", system_number="000999999")
        orphan.id = CatalogRecord.generate_id("MZK01", "000999999")
        db_session.add(orphan)
        db_session.flush()

        marc_by_id = await announce_link_window(
            db_session, [*window_records, orphan.id], ["SKC"], [], logging.getLogger("t")
        )

        assert orphan.id not in marc_by_id
        assert set(marc_by_id) == set(window_records)


@pytest.mark.db
@pytest.mark.redis
class TestTheLinkBringsItsAuthorityRecord:
    def test_reading_system_number_costs_no_second_query(self, db_session, marc_cache_client):
        """`AuthorityLink.system_number` reaches through a lazy relationship."""
        marc_record = load_test_record("MZK01-001217709.mrc")
        main = create_catalog_record(db_session, "MZK01", "000800001", marc_record)
        authority = create_catalog_record(
            db_session,
            "SKC",
            "000800002",
            marc_record,
            source_type=CatalogRecordSource.AuthorityLinker,
        )
        AuthorityLink(
            main_record_id=main.id,
            linker="knihovny-cz",
            base="SKC",
            authority_record_id=authority.id,
        ).save(db_session, commit=False)
        db_session.commit()

        # Read out before expunging: the identity map would otherwise answer
        # the relationship from memory and the test would prove nothing.
        main_id = main.id
        db_session.expunge_all()

        link = AuthorityLink.find_by_main_record_and_base(db_session, main_id, "SKC")
        assert link is not None

        with _CountSelects(db_session) as counted:
            assert link.system_number == "000800002"

        assert counted.count == 0, (
            "reading the authority record's system number went back to the database:\n"
            + "\n".join(counted.statements)
        )

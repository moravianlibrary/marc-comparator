import pytest
from sqlalchemy import text

from catalog_records.analytics import rebuild_all, upsert_records
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.comparison import Comparison


def _create_record(db_session, base="MZK01", sysno="000000001", **kwargs):
    record = CatalogRecord(
        base=base,
        system_number=sysno,
        source_type=CatalogRecordSource.Main,
        **kwargs,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


@pytest.mark.db
class TestRebuildAll:
    def test_populates_table(self, db_session):
        r1 = _create_record(db_session, sysno="000000001")
        r2 = _create_record(db_session, sysno="000000002")

        rebuild_all(db_session)

        rows = db_session.execute(
            text("SELECT id FROM catalog_records_analytics ORDER BY id")
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][0] == r1.id
        assert rows[1][0] == r2.id

    def test_includes_review_status(self, db_session):
        r = _create_record(db_session, sysno="000000001")

        comp = Comparison(
            main_record_id=r.id,
            comparator="Default",
            base="NKC01",
            other_record_id=r.id,
            _result={"overall_score": 0.5, "field_results": []},
        )
        db_session.add(comp)
        db_session.commit()

        rebuild_all(db_session)

        row = db_session.execute(
            text("SELECT review_status FROM catalog_records_analytics WHERE id = :id"),
            {"id": r.id},
        ).fetchone()
        assert row[0] == "Unreviewed"

    def test_authority_linker_source_excluded(self, db_session):
        """Records with source_type=AuthorityLinker should not appear in analytics."""
        _create_record(db_session, sysno="000000001")
        auth = CatalogRecord(
            base="NKC01",
            system_number="000000099",
            source_type=CatalogRecordSource.AuthorityLinker,
        )
        db_session.add(auth)
        db_session.commit()

        rebuild_all(db_session)

        rows = db_session.execute(text("SELECT id FROM catalog_records_analytics")).fetchall()
        assert len(rows) == 1


@pytest.mark.db
class TestUpsertRecords:
    def test_updates_single_row(self, db_session):
        r = _create_record(db_session, sysno="000000001")
        rebuild_all(db_session)

        row = db_session.execute(
            text("SELECT is_deleted FROM catalog_records_analytics WHERE id = :id"),
            {"id": r.id},
        ).fetchone()
        assert row[0] is False

        r.deleted = True
        db_session.commit()

        upsert_records(db_session, [r.id])

        row = db_session.execute(
            text("SELECT is_deleted FROM catalog_records_analytics WHERE id = :id"),
            {"id": r.id},
        ).fetchone()
        assert row[0] is True

    def test_empty_list_is_noop(self, db_session):
        _create_record(db_session, sysno="000000001")
        rebuild_all(db_session)
        upsert_records(db_session, [])

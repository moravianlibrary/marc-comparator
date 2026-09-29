import pytest
from marc_comparator.validators import (
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)
from sqlalchemy import text

from catalog_records.analytics import (
    _ANALYTICS_COLUMNS,
    CREATE_TABLE_SQL,
    TABLE,
    init_analytics_table,
    rebuild_all,
    upsert_records,
)
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.comparison import Comparison

_NEWEST_COLUMN_DDL = "    is_broken       BOOLEAN NOT NULL DEFAULT FALSE,\n"


def _validation_result(status: ValidityStatus) -> dict:
    """A stored validation result, built the way the application builds one.

    Written by hand these fixtures left out ``target``, which the model
    requires, so the rows were a shape no validator could ever produce.
    Building them through the model makes that impossible rather than merely
    corrected.
    """

    return ValidationResult(
        target=ValidationTarget(tag="856", codes=["u"]),
        status=status,
        reason="fixture",
    ).model_dump()


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


@pytest.mark.db
class TestFacetCube:
    """What the cube counts, whichever way it is computed."""

    def population(self, db_session):
        from entities.validation import Validation

        one = _create_record(db_session, sysno="000000001", type_of_record="a")
        two = _create_record(db_session, sysno="000000002", type_of_record="b")
        # No type_of_record at all, so it contributes to no pair on that field.
        three = _create_record(db_session, base="SKC", sysno="000000003")

        db_session.add_all(
            [
                Validation(
                    catalog_record_id=one.id,
                    validator="kramerius-links",
                    result=_validation_result(ValidityStatus.Valid),
                ),
                Validation(
                    catalog_record_id=two.id,
                    validator="kramerius-links",
                    result=_validation_result(ValidityStatus.Valid),
                ),
                Validation(
                    catalog_record_id=two.id,
                    validator="other",
                    result=_validation_result(ValidityStatus.Invalid),
                ),
            ]
        )
        db_session.commit()
        rebuild_all(db_session)
        return one, two, three

    def cube(self, db_session, target_field, target_value):
        rows = db_session.execute(
            text(
                "SELECT facet_field, facet_value, cnt FROM facet_cube "
                "WHERE target_field = :f AND target_value = :v"
            ),
            {"f": target_field, "v": target_value},
        ).all()
        return {(field, value): count for field, value, count in rows}

    def test_totals_count_the_records_holding_a_value(self, db_session):
        self.population(db_session)

        assert self.cube(db_session, "base", "MZK01")[("_total_", "_total_")] == 2
        assert self.cube(db_session, "base", "SKC")[("_total_", "_total_")] == 1

    def test_a_pair_counts_the_records_holding_both(self, db_session):
        self.population(db_session)
        mzk01 = self.cube(db_session, "base", "MZK01")

        assert mzk01[("type_of_record", "a")] == 1
        assert mzk01[("type_of_record", "b")] == 1
        # Both MZK01 records were validated by it; only one by the other.
        assert mzk01[("validators", "kramerius-links")] == 2
        assert mzk01[("validators", "other")] == 1

    def test_pairs_are_counted_from_both_sides(self, db_session):
        self.population(db_session)

        assert self.cube(db_session, "validators", "kramerius-links")[("base", "MZK01")] == 2
        assert self.cube(db_session, "base", "MZK01")[("validators", "kramerius-links")] == 2

    def test_a_field_is_never_paired_with_itself(self, db_session):
        self.population(db_session)

        assert not [key for key in self.cube(db_session, "base", "MZK01") if key[0] == "base"]

    def test_a_null_scalar_contributes_to_nothing(self, db_session):
        self.population(db_session)

        # The SKC record has no type_of_record, so no pair names it.
        assert not [
            key for key in self.cube(db_session, "base", "SKC") if key[0] == "type_of_record"
        ]
        assert self.cube(db_session, "type_of_record", "a").get(("base", "SKC")) is None


@pytest.mark.db
class TestTheTableSurvivesGainingAColumn:
    """The analytics table is created, never migrated.

    `CREATE TABLE IF NOT EXISTS` is a no-op where one already exists, so a new
    column reaches an older deployment through ADD_COLUMNS_SQL — which appends
    it, while CREATE_TABLE_SQL lists it in the middle. An `INSERT ... SELECT`
    matches by position, so on a table that predates the column every value
    after it went into the wrong column and the rebuild failed with a type
    mismatch, aborting whatever task had asked for it.
    """

    def test_a_rebuild_is_correct_on_a_table_that_predates_the_column(self, db_session):
        _create_record(db_session, sysno="000009001", processing_error="will not decode")
        _create_record(db_session, sysno="000009002")

        # Recreate the older shape: same table, without the newest column.
        db_session.execute(text(f"DROP TABLE IF EXISTS {TABLE} CASCADE"))
        db_session.execute(text(CREATE_TABLE_SQL.replace(_NEWEST_COLUMN_DDL, "")))
        db_session.commit()

        init_analytics_table(db_session)
        rebuild_all(db_session)

        rows = dict(
            db_session.execute(
                text(f"SELECT system_number, is_broken FROM {TABLE} ORDER BY system_number")
            ).all()
        )
        assert rows == {"000009001": True, "000009002": False}

    def test_every_named_column_exists_on_the_table(self, db_session):
        init_analytics_table(db_session)

        named = {c.strip() for c in _ANALYTICS_COLUMNS.replace("\n", " ").split(",") if c.strip()}
        actual = {
            row[0]
            for row in db_session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t"
                ),
                {"t": TABLE},
            ).all()
        }

        assert named <= actual, f"the insert names columns the table lacks: {named - actual}"
        assert actual <= named, f"the insert never fills: {actual - named}"

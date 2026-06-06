import pytest

from catalog_records.analytics import rebuild_all
from catalog_records.facets import _facets_live, get_facets
from catalog_records.models import FacetsRequest, RecordFilter
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


def _add_comparison(db_session, record, score, base="NKC01"):
    db_session.add(
        Comparison(
            main_record_id=record.id,
            comparator="Default",
            base=base,
            other_record_id=record.id,
            _result={"overall_score": score, "field_results": []},
        )
    )
    db_session.commit()


def _normalize(response):
    """Facets as {field: {key: count}} so bucket ordering does not matter."""
    return {
        "facets": {f.field: {b.key: b.count for b in f.buckets} for f in response.facets},
        "histograms": {
            h.field: {(b.min, b.max): b.count for b in h.buckets} for h in response.histograms
        },
        "total": response.total,
    }


@pytest.mark.db
class TestGetFacets:
    @pytest.fixture
    def populated(self, db_session):
        r1 = _create_record(db_session, sysno="000000001")
        r2 = _create_record(db_session, sysno="000000002", deleted=True)
        r3 = _create_record(db_session, base="MZK03", sysno="000000003")
        _add_comparison(db_session, r1, 0.95)
        _add_comparison(db_session, r3, 0.42)
        rebuild_all(db_session)  # also rebuilds the cube
        return [r1, r2, r3]

    def test_unfiltered_cube_matches_live(self, db_session, populated):
        """The cube fast-path must produce the same response as live queries."""
        cube_response = get_facets(FacetsRequest(), db_session)
        live_response = _facets_live("WHERE TRUE", {}, db_session)

        assert _normalize(cube_response) == _normalize(live_response)
        assert cube_response.total == 3

    def test_unfiltered_falls_back_when_cube_empty(self, db_session):
        """Before the first rebuild_all the cube is empty - live path answers."""
        from sqlalchemy import text

        from catalog_records.analytics import upsert_records

        r = _create_record(db_session, sysno="000000009")
        upsert_records(db_session, [r.id])  # analytics only, no cube
        db_session.execute(text("TRUNCATE facet_cube"))
        db_session.execute(text("TRUNCATE facet_cube_histogram"))
        db_session.commit()

        response = get_facets(FacetsRequest(), db_session)
        assert response.total == 1

    def test_filtered_uses_live_path(self, db_session, populated):
        response = get_facets(FacetsRequest(filters=RecordFilter(bases=["MZK01"])), db_session)

        assert response.total == 2
        base_facet = next(f for f in response.facets if f.field == "base")
        assert {b.key: b.count for b in base_facet.buckets} == {"MZK01": 2}

    def test_filtered_histogram(self, db_session, populated):
        response = get_facets(FacetsRequest(filters=RecordFilter(bases=["MZK03"])), db_session)

        assert response.histograms
        buckets = response.histograms[0].buckets
        assert sum(b.count for b in buckets) == 1  # one score (0.42) in MZK03
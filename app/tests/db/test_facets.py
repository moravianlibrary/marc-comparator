import pytest

from catalog_records.analytics import rebuild_all
from catalog_records.facets import _facets_live, get_facets, get_facets_preview
from catalog_records.models import FacetsPreviewRequest, FacetsRequest, RecordFilter
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


@pytest.mark.db
class TestPreviewScope:
    """A preview answers for the values asked about, not for every value.

    Each value of an array target costs the live path its own pair of passes
    over the analytics table. ``link_agencies`` has 263 values on this
    install and 187 of them name ten records or fewer, so hovering one pill
    used to run 526 queries — about eighty seconds — to build 263 cross-tabs
    of which the page was rendering twelve.
    """

    @pytest.fixture
    def populated(self, db_session):
        r1 = _create_record(db_session, sysno="000000001")
        r2 = _create_record(db_session, base="MZK03", sysno="000000002")
        _add_comparison(db_session, r1, 0.95, base="NKC01")
        _add_comparison(db_session, r2, 0.42, base="SKC")
        rebuild_all(db_session)
        return [r1, r2]

    def test_the_cube_path_answers_only_for_the_named_values(self, db_session, populated):
        response = get_facets_preview(
            FacetsPreviewRequest(target_field="base", target_values=["MZK01"]), db_session
        )

        assert [p.target_value for p in response.previews] == ["MZK01"]

    def test_the_cube_path_answers_for_everything_when_asked_for_nothing(
        self, db_session, populated
    ):
        """No scope still means every value — the request is a bound, not a filter."""
        response = get_facets_preview(FacetsPreviewRequest(target_field="base"), db_session)

        assert sorted(p.target_value for p in response.previews) == ["MZK01", "MZK03"]

    def test_scoping_does_not_change_what_a_value_says(self, db_session, populated):
        """Narrowing the request must drop entries, never alter the ones left."""
        scoped = get_facets_preview(
            FacetsPreviewRequest(target_field="base", target_values=["MZK01"]), db_session
        )
        unscoped = get_facets_preview(FacetsPreviewRequest(target_field="base"), db_session)

        entry = next(p for p in unscoped.previews if p.target_value == "MZK01")
        assert scoped.previews[0] == entry

    def test_the_live_array_path_answers_only_for_the_named_values(self, db_session, populated):
        """The expensive path: one scan per value, so the scope is the saving."""
        response = get_facets_preview(
            FacetsPreviewRequest(
                filters=RecordFilter(bases=["MZK01", "MZK03"]),
                target_field="comparison_bases",
                target_values=["NKC01"],
            ),
            db_session,
        )

        assert [p.target_value for p in response.previews] == ["NKC01"]
        assert response.previews[0].total == 1

    def test_the_live_array_path_answers_for_everything_when_asked_for_nothing(
        self, db_session, populated
    ):
        response = get_facets_preview(
            FacetsPreviewRequest(
                filters=RecordFilter(bases=["MZK01", "MZK03"]),
                target_field="comparison_bases",
            ),
            db_session,
        )

        assert sorted(p.target_value for p in response.previews) == ["NKC01", "SKC"]

    def test_a_value_that_is_not_there_is_simply_absent(self, db_session, populated):
        """The client sends what it is showing; stale pills must not be an error."""
        response = get_facets_preview(
            FacetsPreviewRequest(
                filters=RecordFilter(bases=["MZK01"]),
                target_field="comparison_bases",
                target_values=["NKC01", "SKC"],
            ),
            db_session,
        )

        assert [p.target_value for p in response.previews] == ["NKC01"]

    def test_the_live_array_path_reports_the_scalar_facets(self, db_session, populated):
        """The regression this class caught on the way past.

        Two of the three GROUPING SETS queries learned to select ``GROUPING``
        flags when the booleans became nullable and this one did not, so the
        parsers that read those flags raised ``NoSuchColumnError`` and every
        filtered preview of an array facet answered 500.
        """
        response = get_facets_preview(
            FacetsPreviewRequest(
                filters=RecordFilter(bases=["MZK01", "MZK03"]),
                target_field="comparison_bases",
            ),
            db_session,
        )

        entry = next(p for p in response.previews if p.target_value == "NKC01")
        base_facet = next(f for f in entry.facets if f.field == "base")
        assert {b.key: b.count for b in base_facet.buckets} == {"MZK01": 1}

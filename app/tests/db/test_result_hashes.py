"""Reading a window's results must give each record what it would read alone."""

import pytest

from catalog_records.tasks import _compute_result_hashes, _result_hashes_for
from entities.catalog_record import CatalogRecord, CatalogRecordSource
from entities.comparison import Comparison
from entities.validation import Validation

pytestmark = pytest.mark.db


def record(db_session, sysno: str) -> CatalogRecord:
    row = CatalogRecord(base="MZK01", system_number=sysno, source_type=CatalogRecordSource.Main)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def population(db_session):
    """One record with both aspects, one with either, one with neither."""

    both = record(db_session, "000000001")
    compared_only = record(db_session, "000000002")
    validated_only = record(db_session, "000000003")
    bare = record(db_session, "000000004")

    db_session.add_all(
        [
            Comparison(
                main_record_id=both.id,
                comparator="default",
                base="SKC",
                other_record_id=both.id,
                result={"overall_score": 0.91},
            ),
            Comparison(
                main_record_id=compared_only.id,
                comparator="default",
                base="SKC",
                other_record_id=compared_only.id,
                result={"overall_score": 0.42},
            ),
            Validation(
                catalog_record_id=both.id,
                validator="kramerius-links",
                result={"status": "Valid"},
            ),
            Validation(
                catalog_record_id=validated_only.id,
                validator="kramerius-links",
                result={"status": "Invalid"},
            ),
        ]
    )
    db_session.commit()
    return [both.id, compared_only.id, validated_only.id, bare.id]


def test_the_window_gives_each_record_what_it_would_read_alone(db_session, population):
    windowed = _result_hashes_for(db_session, population)
    singly = {record_id: _compute_result_hashes(db_session, record_id) for record_id in population}

    assert windowed == singly
    # Not vacuous: the aspects really are there, and differ between records.
    assert set(singly[population[0]]) == {"default", "kramerius-links"}
    assert set(singly[population[1]]) == {"default"}
    assert set(singly[population[2]]) == {"kramerius-links"}


def test_a_record_with_no_results_has_no_aspects(db_session, population):
    assert _result_hashes_for(db_session, population)[population[3]] == {}


def test_a_record_outside_the_window_is_absent(db_session, population):
    # The caller falls back to the per-record read for anything missing.
    assert "MZK01-999999999" not in _result_hashes_for(db_session, population)


def test_asking_for_nothing_reads_nothing(db_session):
    assert _result_hashes_for(db_session, []) == {}

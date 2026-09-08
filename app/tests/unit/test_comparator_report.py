"""Unit tests for BaseComparator.generate_report (CSV analysis table)."""

import csv
import io

from marc_comparator.comparators import (
    ComparisonReportInput,
    DefaultComparator,
    DefaultComparatorConfig,
    Explanation,
    FieldComparisonResult,
    RecordComparisonResult,
    SubfieldComparisonResult,
)


def make_comparator() -> DefaultComparator:
    return DefaultComparator(DefaultComparatorConfig())


def parse_csv(content: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def test_report_has_one_row_per_subfield():
    result = RecordComparisonResult(
        overall_score=0.55,
        summary="x",
        field_results=[
            FieldComparisonResult(
                tag="245",
                score=0.5,
                explanation=Explanation.Typo,
                subfield_results=[
                    SubfieldComparisonResult(
                        code="a",
                        value_a="Foo",
                        value_b="Foo!",
                        score=0.5,
                        explanation=Explanation.Typo,
                    ),
                    SubfieldComparisonResult(
                        code="b",
                        value_a="Bar",
                        value_b=None,
                        score=0.0,
                        explanation=Explanation.Missing,
                    ),
                ],
            )
        ],
    )
    files = make_comparator().generate_report(
        [
            ComparisonReportInput(
                catalog_record_id="MZK01-1", base="AUT", other_record_id="AUT-9", result=result
            )
        ]
    )

    assert len(files) == 1
    assert files[0].filename == "comparator_report.csv"
    assert files[0].content_type == "text/csv"

    rows = parse_csv(files[0].content)
    assert len(rows) == 2
    assert rows[0]["field_tag"] == "245"
    assert rows[0]["subfield_code"] == "a"
    assert rows[0]["value_a"] == "Foo"
    assert rows[0]["value_b"] == "Foo!"
    assert rows[0]["explanation"] == "Typo"
    assert rows[1]["subfield_code"] == "b"
    assert rows[1]["explanation"] == "Missing"
    assert rows[0]["overall_score"] == "0.55"


def test_field_without_subfields_yields_one_row():
    result = RecordComparisonResult(
        overall_score=0.8,
        field_results=[
            FieldComparisonResult(
                tag="020",
                value_a="123",
                value_b="123",
                score=1.0,
                explanation=Explanation.Identical,
            )
        ],
    )
    files = make_comparator().generate_report(
        [
            ComparisonReportInput(
                catalog_record_id="MZK01-2", base="AUT", other_record_id="AUT-8", result=result
            )
        ]
    )
    rows = parse_csv(files[0].content)
    assert len(rows) == 1
    assert rows[0]["field_tag"] == "020"
    assert rows[0]["subfield_code"] == ""


def test_empty_input_yields_header_only():
    files = make_comparator().generate_report([])
    rows = parse_csv(files[0].content)
    assert rows == []

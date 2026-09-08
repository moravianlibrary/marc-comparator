"""Unit tests for KrameriusLinksValidator.generate_report (856 .seq repair port).

Builds synthetic MARC records + validation results (no DB, no network) and
asserts the Aleph sequential output for each reason -> action mapping.
"""

from marc_comparator.validators import (
    ReportInput,
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)
from marc_comparator.validators.kramerius_links import (
    STANDARD_LINK_TEXT,
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from marcdantic import MarcRecord

LEADER = "00000nam a2200000 a 4500"
CID = "MZK01-000042660"
SYSNO = "000042660"


def make_validator() -> KrameriusLinksValidator:
    return KrameriusLinksValidator(KrameriusLinksValidatorConfig())


def make_record(fields_856: list[dict]) -> MarcRecord:
    return MarcRecord.model_validate(
        {
            "leader": LEADER,
            "fixed_fields": {
                "001": SYSNO,
                "005": "20200101000000.0",
                "008": "200101s2020    xr            000 0 cze d",
            },
            "variable_fields": {"856": fields_856} if fields_856 else {},
        }
    )


def result(reason: str, *, field_index=None, params=None, status=ValidityStatus.Invalid):
    return ValidationResult(
        status=status,
        target=ValidationTarget(tag="856", codes=["u", "y"], field_index=field_index),
        reason=reason,
        params=params,
    )


def seq_files(files):
    return {f.filename: f.content.decode("utf-8") for f in files}


def test_missing_link_text_adds_y_and_keeps_u():
    url = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:abc"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [url]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "missing_link_text",
                field_index=0,
                params={"pattern": STANDARD_LINK_TEXT},
                status=ValidityStatus.ForReview,
            )
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert "aleph_seq_MZK01.seq" in files
    line = files["aleph_seq_MZK01.seq"].strip()
    assert line.startswith(f"{SYSNO} 85641 L ")
    assert f"$$u{url}" in line
    assert f"$$y{STANDARD_LINK_TEXT}" in line


def test_link_not_found_removes_field_and_marks_for_deletion():
    url = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:dead"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [url]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("link_not_found", field_index=0, params={"pid": "uuid:dead"})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    # No 856 left -> no seq file, sysno goes to the delete list.
    assert "aleph_seq_MZK01.seq" not in files
    assert files["aleph_delete_856_MZK01.txt"].strip() == SYSNO


def test_missing_link_in_marc_adds_new_856():
    record = make_record([])  # no 856 at all
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("missing_link_in_marc", params={"pid": "uuid:new1"})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    line = files["aleph_seq_MZK01.seq"].strip()
    assert "$$uhttps://www.digitalniknihovna.cz/mzk/uuid/uuid:new1" in line
    assert f"$$y{STANDARD_LINK_TEXT}" in line


def test_wrong_path_found_replaces_u():
    wrong = "https://www.digitalniknihovna.cz/mzk/view/uuid:pathfix"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [wrong]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "wrong_path_found",
                field_index=0,
                params={
                    "pid": "uuid:pathfix",
                    "value": wrong,
                    "url": "https://www.digitalniknihovna.cz/mzk/uuid/{pid}",
                },
                status=ValidityStatus.AdditionalInfo,
            )
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))
    line = files["aleph_seq_MZK01.seq"].strip()
    assert "$$uhttps://www.digitalniknihovna.cz/mzk/uuid/uuid:pathfix" in line
    assert wrong not in line


def test_wrong_server_found_removes_and_readds():
    wrong = "https://kramerius.old.cz/handle/uuid:srv"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [wrong]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "wrong_server_found",
                field_index=0,
                params={
                    "pid": "uuid:srv",
                    "value": wrong,
                    "url": "https://www.digitalniknihovna.cz/mzk/uuid/{pid}",
                },
            )
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))
    line = files["aleph_seq_MZK01.seq"].strip()
    assert wrong not in line
    assert "$$uhttps://www.digitalniknihovna.cz/mzk/uuid/uuid:srv" in line


def test_non_actionable_reason_produces_no_files():
    url = "not-a-valid-url"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [url]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("invalid_link_format", field_index=0, params={"value": url})],
    )

    files = make_validator().generate_report([inp])
    assert files == []


def test_out_of_range_field_index_recorded_in_errors():
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": ["x"]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "wrong_path_found",
                field_index=5,
                params={"pid": "uuid:oor"},
                status=ValidityStatus.AdditionalInfo,
            )
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))
    assert "errors.json" in files
    assert "out of range" in files["errors.json"]

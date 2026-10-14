"""Unit tests for KrameriusLinksValidator.generate_report (856 .seq repair port).

Builds synthetic MARC records + validation results (no DB, no network) and
asserts the Aleph sequential output for each reason -> action mapping.
"""

import pytest
from marc_comparator.validators import (
    ReportInput,
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)
from marc_comparator.validators.kramerius_links import (
    NORMALIZATION_REASONS,
    REASON_STATUS,
    REPAIR_REASONS,
    STANDARD_LINK_TEXT,
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from marcdantic import MarcRecord

LEADER = "00000nam a2200000 a 4500"
SEQ_REPAIR = "aleph_repair_MZK01.seq"
SEQ_NORMALIZE = "aleph_normalization_MZK01.seq"
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


def result(reason: str, *, field_index=None, params=None, status=None):
    return ValidationResult(
        status=status or REASON_STATUS[reason],
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

    assert SEQ_NORMALIZE in files
    line = files[SEQ_NORMALIZE].strip()
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
    assert SEQ_REPAIR not in files
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

    line = files[SEQ_REPAIR].strip()
    assert "$$uhttps://www.digitalniknihovna.cz/mzk/uuid/uuid:new1" in line
    assert f"$$y{STANDARD_LINK_TEXT}" in line


def test_non_canonical_url_found_replaces_u():
    wrong = "https://www.digitalniknihovna.cz/mzk/view/uuid:pathfix"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [wrong]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "non_canonical_url_found",
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
    line = files[SEQ_NORMALIZE].strip()
    assert "$$uhttps://www.digitalniknihovna.cz/mzk/uuid/uuid:pathfix" in line
    assert wrong not in line


def test_legacy_host_url_is_normalised():
    wrong = "http://kramerius.mzk.cz/search/handle/uuid:srv"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [wrong]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "non_canonical_url_found",
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
    line = files[SEQ_NORMALIZE].strip()
    assert wrong not in line
    assert "$$uhttps://www.digitalniknihovna.cz/mzk/uuid/uuid:srv" in line


def test_non_repairable_reason_produces_a_review_csv_and_no_seq():
    """Nothing to apply, but a person still has to see it.

    The reason has no automated fix, so neither .seq may mention the record.
    Dropping it entirely was the old behaviour and meant a finding nobody
    could act on was also a finding nobody was told about.
    """

    url = "not-a-valid-url"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [url]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("invalid_link_format", field_index=0, params={"value": url})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert SEQ_REPAIR not in files
    assert SEQ_NORMALIZE not in files
    assert url in files["review_invalid_link_format.csv"]


def test_out_of_range_field_index_recorded_in_errors():
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": ["x"]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "non_canonical_url_found",
                field_index=5,
                params={"pid": "uuid:oor"},
                status=ValidityStatus.AdditionalInfo,
            )
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))
    assert "errors.json" in files
    assert "out of range" in files["errors.json"]


# ── $x / $z preservation ─────────────────────────────────────────────────────
#
# Neither is invented for a new link, but a repair must never destroy what a
# cataloguer wrote — it cannot be reconstructed from Kramerius.


def test_url_repair_preserves_existing_x_and_z():
    """Cataloguers' $x and $z must survive a URL fix — they cannot be reconstructed."""
    old = "https://www.digitalniknihovna.cz/mzk/view/uuid:abc"
    record = make_record(
        [
            {
                "ind1": "4",
                "ind2": "1",
                "subfields": {
                    "u": [old],
                    "y": [STANDARD_LINK_TEXT],
                    "x": ["NDK"],
                    "z": ["Díl 2"],
                },
            }
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result("non_canonical_url_found", field_index=0, params={"pid": "uuid:abc"}),
        ],
    )
    line = seq_files(make_validator().generate_report([inp]))[SEQ_NORMALIZE].strip()

    assert "$$xNDK" in line
    assert "$$zDíl 2" in line
    assert "/mzk/uuid/uuid:abc" in line
    assert "/mzk/view/" not in line


def test_legacy_host_repair_preserves_x_and_z():
    """Same for the legacy host: rewrite $u in place, do not drop the field."""
    record = make_record(
        [
            {
                "ind1": "4",
                "ind2": "1",
                "subfields": {
                    "u": ["http://kramerius.mzk.cz/search/handle/uuid:abc"],
                    "y": [STANDARD_LINK_TEXT],
                    "x": ["NDK"],
                    "z": ["2014/27"],
                },
            }
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("non_canonical_url_found", field_index=0, params={"pid": "uuid:abc"})],
    )
    line = seq_files(make_validator().generate_report([inp]))[SEQ_NORMALIZE].strip()

    assert line.count("$$u") == 1
    assert "$$xNDK" in line
    assert "$$z2014/27" in line
    assert "kramerius.mzk.cz" not in line


# ── repair / normalisation split ─────────────────────────────────────────────


def test_a_repair_and_a_normalisation_land_in_separate_files():
    """A broken link and an untidy one must not travel together.

    Both edit the same record, so a single file would mean applying 8,870
    cosmetic rewrites to get at 28,782 real fixes. Which of the two to run is
    a cataloguer's decision, and it only stays a decision while they are
    separate artefacts.
    """

    stale = "https://www.digitalniknihovna.cz/mzk/view/uuid:tidy"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [stale]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result("non_canonical_url_found", field_index=0, params={"pid": "uuid:tidy"}),
            result("missing_link_in_marc", params={"pid": "uuid:added"}),
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert "uuid:added" in files[SEQ_REPAIR]
    assert "/mzk/view/" in files[SEQ_REPAIR], "the untidy link is carried over, not fixed"
    assert "/mzk/uuid/uuid:tidy" in files[SEQ_NORMALIZE]
    assert "uuid:added" not in files[SEQ_NORMALIZE]


def test_reasons_are_split_between_the_two_passes_and_never_shared():
    assert not REPAIR_REASONS & NORMALIZATION_REASONS


def test_a_record_is_deleted_only_when_no_856_survives():
    """A removal is not a deletion while any other 856 remains."""

    dead = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:gone"
    record = make_record(
        [
            {"ind1": "4", "ind2": "1", "subfields": {"u": [dead]}},
            {"ind1": "4", "ind2": "1", "subfields": {"u": ["https://example.org/unrelated"]}},
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("link_not_found", field_index=0, params={"pid": "uuid:gone"})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert "aleph_delete_856_MZK01.txt" not in files
    assert "https://example.org/unrelated" in files[SEQ_REPAIR]
    assert "uuid:gone" not in files[SEQ_REPAIR]


def test_a_not_found_link_is_removed_rather_than_canonicalised():
    """Rewriting it would only turn a dead link into a tidy dead link."""

    dead = "https://www.digitalniknihovna.cz/mzk/view/uuid:gone"
    record = make_record(
        [
            {"ind1": "4", "ind2": "1", "subfields": {"u": [dead]}},
            {"ind1": "4", "ind2": "1", "subfields": {"u": ["https://example.org/unrelated"]}},
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("non_canonical_url_not_found", field_index=0, params={"pid": "uuid:gone"})],
    )

    line = seq_files(make_validator().generate_report([inp]))[SEQ_REPAIR]

    assert "uuid:gone" not in line


# ── what a repair may not touch ──────────────────────────────────────────────


def test_only_the_u_naming_the_pid_is_rewritten():
    """An 856 may carry more than one $u; the others are not ours to drop."""

    target = "https://www.digitalniknihovna.cz/mzk/view/uuid:one"
    other = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:two"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [target, other]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("non_canonical_url_found", field_index=0, params={"pid": "uuid:one"})],
    )

    line = seq_files(make_validator().generate_report([inp]))[SEQ_NORMALIZE].strip()

    assert "$$uhttps://www.digitalniknihovna.cz/mzk/uuid/uuid:one" in line
    assert f"$$u{other}" in line
    assert "/mzk/view/" not in line


def test_an_existing_link_text_is_never_overwritten():
    url = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:abc"
    record = make_record(
        [{"ind1": "4", "ind2": "1", "subfields": {"u": [url], "y": ["Cataloguer's own words"]}}]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("missing_link_text", field_index=0, params={})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert "Cataloguer's own words" in files[SEQ_NORMALIZE]
    assert STANDARD_LINK_TEXT not in files[SEQ_NORMALIZE]


def test_a_new_link_text_follows_its_url_rather_than_trailing_the_field():
    url = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:abc"
    record = make_record(
        [{"ind1": "4", "ind2": "1", "subfields": {"u": [url], "x": ["NDK"], "z": ["sv. 2"]}}]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("missing_link_text", field_index=0, params={})],
    )

    line = seq_files(make_validator().generate_report([inp]))[SEQ_NORMALIZE].strip()

    assert line.index("$$y") < line.index("$$x") < line.index("$$z")


def test_indicators_of_an_untouched_field_survive():
    record = make_record(
        [
            {"ind1": "4", "ind2": "0", "subfields": {"u": ["https://example.org/keep"]}},
            {
                "ind1": "4",
                "ind2": "1",
                "subfields": {"u": ["https://www.digitalniknihovna.cz/mzk/view/uuid:fix"]},
            },
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("non_canonical_url_found", field_index=1, params={"pid": "uuid:fix"})],
    )

    lines = seq_files(make_validator().generate_report([inp]))[SEQ_NORMALIZE].strip().splitlines()

    assert any(line.startswith(f"{SYSNO} 85640 L ") for line in lines)


# ── review CSVs ──────────────────────────────────────────────────────────────


def test_every_reported_reason_without_a_fix_gets_its_own_csv():
    record = make_record(
        [{"ind1": "4", "ind2": "1", "subfields": {"u": ["https://kramerius.lib.cas.cz/uuid/x"]}}]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "foreign_digital_library",
                field_index=0,
                params={"value": "https://kramerius.lib.cas.cz/uuid/x"},
            ),
            result("missing_link_in_marc", params={"pid": "uuid:ours"}),
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))
    csv_text = files["review_foreign_digital_library.csv"]

    assert "kramerius.lib.cas.cz" in csv_text
    # The one thing worth knowing about a link into another library.
    assert "mzk_copy_available" in csv_text.splitlines()[0]
    assert "True" in csv_text.splitlines()[1]


def test_a_client_url_we_would_not_accept_stops_the_report():
    """The settings must agree before anything is written.

    `kramerius_client_url` and the two patterns are edited independently. If
    what we write is not what we call canonical, every repair emits a link
    the next pass reports as non-canonical and rewrites again — the same
    records churning through a normalisation file forever. Harvesting does
    not care, so this is refused where it would do damage rather than at
    construction.
    """

    validator = KrameriusLinksValidator(
        KrameriusLinksValidatorConfig(
            kramerius_client_url="https://www.digitalniknihovna.cz/mzk/view/{pid}"
        )
    )
    record = make_record([])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("missing_link_in_marc", params={"pid": "uuid:x"})],
    )

    with pytest.raises(ValueError, match="canonical"):
        validator.generate_report([inp])

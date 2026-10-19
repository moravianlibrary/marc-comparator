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
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from marcdantic import MarcRecord

#: What a repair writes into $y, now a setting rather than a constant.
STANDARD_LINK_TEXT = KrameriusLinksValidatorConfig().link_text

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


def test_a_record_needing_both_is_repaired_and_tidied_in_one_block():
    """A record being mended is tidied on the way through.

    Separate files are only independent while no record is in both: each
    rewrites the whole 856 block of every sysno it names, so a record in both
    means whichever Aleph loads second reverts the other. The repair takes
    it — and since the block is being rewritten wholesale either way, the
    tidying rides along for free. Leaving it out would emit one block holding
    both spellings of the link text at once.
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
    assert "/mzk/view/" not in files[SEQ_REPAIR], "the untidy link is canonicalised too"
    assert "/mzk/uuid/uuid:tidy" in files[SEQ_REPAIR]
    assert SEQ_NORMALIZE not in files, "the record is claimed by the repair pass"


def test_a_record_needing_only_tidying_stays_out_of_the_repair_file():
    """The guard on the pass above.

    The repair pass reads normalisation reasons so it can tidy what it mends,
    which is only safe while a record with nothing to mend cannot reach it.
    Otherwise repairing a batch would drag along a mass rewrite of every
    record written in an older URL form — the churn the two files exist to
    keep apart.
    """

    stale = "https://www.digitalniknihovna.cz/mzk/view/uuid:tidy"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [stale]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("non_canonical_url_found", field_index=0, params={"pid": "uuid:tidy"})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert SEQ_REPAIR not in files
    assert "/mzk/uuid/uuid:tidy" in files[SEQ_NORMALIZE]


def test_a_record_in_both_files_stops_the_report():
    """The guard behind the rule, for the day repair-wins is changed away.

    Checked rather than reviewed because the failure is invisible in either
    file on its own: both look right, and only the order Aleph loads them in
    decides which record keeps its fix.
    """

    plugin = make_validator()
    lines = {
        ("repair", "MZK01"): [f"{SYSNO} 85641 L $$uhttps://example.test/a"],
        ("normalization", "MZK01"): [f"{SYSNO} 85641 L $$uhttps://example.test/b"],
    }

    with pytest.raises(ValueError, match="more than one"):
        plugin._refuse_overlap(lines, {})


def test_a_deleted_record_may_not_also_be_rewritten():
    plugin = make_validator()
    lines = {("repair", "MZK01"): [f"{SYSNO} 85641 L $$uhttps://example.test/a"]}

    with pytest.raises(ValueError, match="more than one"):
        plugin._refuse_overlap(lines, {"MZK01": [SYSNO]})


def test_the_two_files_naming_different_records_is_fine():
    plugin = make_validator()
    lines = {
        ("repair", "MZK01"): ["000000001 85641 L $$uhttps://example.test/a"],
        ("normalization", "MZK01"): ["000000002 85641 L $$uhttps://example.test/b"],
    }

    plugin._refuse_overlap(lines, {"MZK01": ["000000003"]})


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


def test_a_link_text_that_does_not_match_is_replaced():
    """The finding is raised about the wording, so the wording is what changes.

    Filling only an empty $y left 1,742 of 1,758 findings unrepaired while
    still writing the record out, which is how a .seq that was 29% no-op
    rewrites went unnoticed. Anything the configured pattern accepts is never
    reported in the first place, so a cataloguer's own elaboration — the 9,126
    fields reading "... (klikněte pro zobrazení)" — never reaches here.
    """

    url = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:abc"
    record = make_record(
        [{"ind1": "4", "ind2": "1", "subfields": {"u": [url], "y": ["Digitalizovan dokument"]}}]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("missing_link_text", field_index=0, params={})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert f"$$y{STANDARD_LINK_TEXT}" in files[SEQ_NORMALIZE]
    assert "Digitalizovan dokument$" not in files[SEQ_NORMALIZE]


def test_a_pass_that_changes_nothing_writes_nothing():
    """An edit that applied to no field must not still rewrite the record.

    Under REPLACE-ALL a record in the file is a full wipe and reload of its
    856 block, so emitting one that comes back byte-identical is work Aleph
    does for nothing — and it hides the finding that failed to apply.
    """

    url = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:abc"
    record = make_record([{"ind1": "4", "ind2": "1", "subfields": {"u": [url]}}])
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        # Points past the end of the record, so nothing is applied.
        results=[result("missing_link_text", field_index=7, params={})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert SEQ_NORMALIZE not in files


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
                "other_online_resource",
                field_index=0,
                params={"value": "https://kramerius.lib.cas.cz/uuid/x"},
            ),
            result("missing_link_in_marc", params={"pid": "uuid:ours"}),
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))
    csv_text = files["review_other_online_resource.csv"]

    assert "kramerius.lib.cas.cz" in csv_text
    # The one thing worth knowing about a copy held somewhere else.
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


PID_A = "uuid:11111111-2222-3333-4444-555555555555"
CANON_A = f"https://www.digitalniknihovna.cz/mzk/uuid/{PID_A}"


def test_a_link_already_held_in_an_older_url_form_is_not_added_again():
    """Links are compared by document, not by URL text.

    `/view/uuid:X` and `/uuid/uuid:X` are one link to one place. Matching on
    the string let the second through beside the first, and under REPLACE-ALL
    both reach the catalogue.
    """

    dead = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:dead"
    record = make_record(
        [
            {
                "ind1": "4",
                "ind2": "1",
                "subfields": {"u": [f"https://www.digitalniknihovna.cz/mzk/view/{PID_A}"]},
            },
            {"ind1": "4", "ind2": "1", "subfields": {"u": [dead]}},
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result("missing_link_in_marc", params={"pid": PID_A}),
            # A real repair, so the pass writes the record out and the
            # suppressed addition is visible by its absence rather than by
            # the whole file being skipped.
            result("link_not_found", field_index=1, params={"pid": "uuid:dead"}),
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert files[SEQ_REPAIR].count(PID_A) == 1
    assert "uuid:dead" not in files[SEQ_REPAIR]


def test_a_copy_in_another_library_does_not_block_adding_ours():
    """The same uuid at ndk.cz is their copy, not ours.

    Suppressing our link because somebody else's URL carries that uuid is the
    opposite of what the report is for: `mzk_copy_available` exists to say we
    are adding one alongside.
    """

    record = make_record(
        [{"ind1": "4", "ind2": "1", "subfields": {"u": [f"https://ndk.cz/uuid/{PID_A}"]}}]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("missing_link_in_marc", params={"pid": PID_A})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert "ndk.cz" in files[SEQ_REPAIR]
    assert CANON_A in files[SEQ_REPAIR]


def test_a_rewrite_that_lands_on_a_link_already_there_collapses():
    """Only a field another one says everything of is dropped."""

    record = make_record(
        [
            {
                "ind1": "4",
                "ind2": "1",
                "subfields": {"u": [f"https://www.digitalniknihovna.cz/mzk/view/{PID_A}"]},
            },
            {"ind1": "4", "ind2": "1", "subfields": {"u": [CANON_A]}},
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("non_canonical_url_found", field_index=0, params={"pid": PID_A})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert files[SEQ_NORMALIZE].count(PID_A) == 1


def test_two_volumes_of_one_document_are_both_kept():
    """A $z the other field does not carry is something only it says."""

    record = make_record(
        [
            {
                "ind1": "4",
                "ind2": "1",
                "subfields": {
                    "u": [f"https://www.digitalniknihovna.cz/mzk/view/{PID_A}"],
                    "z": ["Svazek 1"],
                },
            },
            {"ind1": "4", "ind2": "1", "subfields": {"u": [CANON_A], "z": ["Svazek 2"]}},
        ]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("non_canonical_url_found", field_index=0, params={"pid": PID_A})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert "Svazek 1" in files[SEQ_NORMALIZE]
    assert "Svazek 2" in files[SEQ_NORMALIZE]


def test_a_review_csv_names_the_url_even_when_the_finding_did_not():
    """`missing_link_text` records only the pattern it failed to match.

    Left as-is the column is blank on every row, in front of the person whose
    job is to judge the link. The record is in hand, so the field the finding
    points at supplies it.
    """

    url = "https://www.digitalniknihovna.cz/mzk/uuid/uuid:abc"
    record = make_record(
        [{"ind1": "4", "ind2": "1", "subfields": {"u": [url], "y": ["Digitalizovan dokument"]}}]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[result("missing_link_text", field_index=0, params={})],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert url in files["review_missing_link_text.csv"]


def test_a_link_below_the_top_is_reported_rather_than_repaired():
    record = make_record(
        [{"ind1": "4", "ind2": "1", "subfields": {"u": [CANON_A], "z": ["Svazek 2"]}}]
    )
    inp = ReportInput(
        catalog_record_id=CID,
        base="MZK01",
        marc=record,
        results=[
            result(
                "non_top_level_document",
                field_index=0,
                params={
                    "pid": PID_A,
                    "model": "monographunit",
                    "level": "1",
                    "top_level_pid": "uuid:99999999-9999-9999-9999-999999999999",
                },
            )
        ],
    )

    files = seq_files(make_validator().generate_report([inp]))

    assert SEQ_REPAIR not in files, "the volume link is left exactly as the cataloguer wrote it"
    csv_text = files["review_non_top_level_document.csv"]
    assert "monographunit" in csv_text
    assert "uuid:99999999-9999-9999-9999-999999999999" in csv_text

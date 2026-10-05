"""Whose record it is decides how strictly it is parsed.

A record we sync is ours to fix, so a missing mandatory field means the record
is broken and it says so. A match candidate fetched from the union catalogue is
neither ours to fix nor ours to record — there is no row to call broken — so
refusing it only shrinks the candidate pool and costs recall on our own
records, silently and at WARNING level.
"""

import lxml.etree as etree
import pytest
from marc_comparator.authority_linkers._base import CANDIDATE_MARC_CONTEXT
from marcdantic import MarcRecord
from marcdantic.context import MarcContext
from pydantic import ValidationError

MARC_NS = "http://www.loc.gov/MARC21/slim"


def _xml(*, control=("001", "005", "008"), subfields='<subfield code="a">Title</subfield>'):
    fields = "".join(f'<controlfield tag="{t}">000000</controlfield>' for t in control)
    return etree.fromstring(
        f'<record xmlns="{MARC_NS}">'
        "<leader>00000nam a2200000 a 4500</leader>"
        f"{fields}"
        f'<datafield tag="245" ind1="1" ind2="0">{subfields}</datafield>'
        "</record>".encode()
    )


class TestACandidateIsParsedLeniently:
    def test_a_union_catalogue_record_with_no_005_is_usable(self):
        """The failure this was reached from.

        `Missing mandatory MARC field(s): 005` took MZK01-000097158's whole
        lookup down, and 005 is the date of the record's latest transaction —
        which says nothing about whether two records describe the same book.
        """

        record = MarcRecord.from_xml(_xml(control=("001", "008")), CANDIDATE_MARC_CONTEXT)

        assert record.fixed_fields.root["001"] == "000000"

    def test_001_is_still_required_of_a_candidate(self):
        # Without it there is nothing to link to.
        with pytest.raises(ValidationError):
            MarcRecord.from_xml(_xml(control=("008",)), CANDIDATE_MARC_CONTEXT)


class TestOurOwnRecordsAreStillHeldToTheDefault:
    def test_a_synced_record_missing_005_is_still_refused(self):
        with pytest.raises(ValidationError) as caught:
            MarcRecord.from_xml(_xml(control=("001", "008")))

        assert "005" in str(caught.value)

    def test_a_synced_record_missing_008_is_still_refused(self):
        with pytest.raises(ValidationError) as caught:
            MarcRecord.from_xml(_xml(control=("001", "005")))

        assert "008" in str(caught.value)


class TestReadingBackWhatWeChoseToKeep:
    """The trap in relaxing only the door.

    Admitting a 005-less candidate and then holding its stored form to the
    default would write rows that cannot be read back — every later
    comparison, validation and report of a record that linked perfectly well
    would fail. The check belongs at the boundary, not on every read.
    """

    def test_a_stored_record_missing_005_can_be_read_again(self):
        from adapters.marc_sectors import read_stored_marc

        admitted = MarcRecord.from_xml(_xml(control=("001",)), CANDIDATE_MARC_CONTEXT)
        assert admitted._marc is not None

        reread = read_stored_marc(admitted._marc)

        assert reread.fixed_fields.root["001"] == "000000"

    def test_the_stored_context_asks_for_nothing(self):
        from adapters.marc_sectors import STORED_MARC_CONTEXT

        assert STORED_MARC_CONTEXT.mandatory_fields == []


class TestAnEmptySubfieldNoLongerKillsTheRecord:
    def test_a_subfield_with_no_text_is_dropped_not_fatal(self):
        record = MarcRecord.from_xml(
            _xml(subfields='<subfield code="a">Title</subfield><subfield code="b"/>')
        )

        subfields = record.variable_fields.root["245"][0].subfields
        assert subfields["a"] == ["Title"]
        assert "b" not in subfields

    def test_the_raw_bytes_do_not_spell_none(self):
        record = MarcRecord.from_xml(
            _xml(subfields='<subfield code="a">Title</subfield><subfield code="b"/>')
        )

        assert b"None" not in (record._marc or b"")


def test_the_two_contexts_are_different_questions():
    assert CANDIDATE_MARC_CONTEXT.mandatory_fields == ["001"]
    assert MarcContext().mandatory_fields == ["001", "005", "008"]

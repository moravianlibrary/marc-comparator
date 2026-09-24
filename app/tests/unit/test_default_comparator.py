"""Which tags the comparator reads positionally, and what it does with the rest."""

import pytest
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]  # lxml ships no stubs
from marc_comparator.comparators import default as default_comparator
from marc_comparator.comparators.default import (
    DefaultComparator,
    DefaultComparatorConfig,
    _is_fixed_field_tag,
)
from marcdantic import MarcRecord

MARC_XML = """
<record xmlns="http://www.loc.gov/MARC21/slim">
  <leader>     nam a22      a 4500</leader>
  <controlfield tag="001">mzk00001</controlfield>
  <controlfield tag="005">20170113091406.0</controlfield>
  <controlfield tag="008">120529s2012    xr a   f f    000 0 cze d</controlfield>
  <datafield tag="336" ind1=" " ind2=" ">
    <subfield code="a">text</subfield>
    <subfield code="b">txt</subfield>
    <subfield code="2">rdacontent</subfield>
  </datafield>
</record>
"""


def marc_record() -> MarcRecord:
    return MarcRecord.from_xml(etree.fromstring(MARC_XML.strip().encode()))


@pytest.mark.parametrize("tag", ["000", "001", "005", "008", "009"])
def test_00x_block_is_fixed(tag: str) -> None:
    assert _is_fixed_field_tag(tag)


@pytest.mark.parametrize("tag", ["010", "100", "245", "336", "856", "LDR", ""])
def test_everything_else_is_variable(tag: str) -> None:
    assert not _is_fixed_field_tag(tag)


async def test_whole_field_diff_does_not_fail_the_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A codeless group on a variable field used to be read as a fixed field.

    The engine reports a variable field it compared as a whole with no subfield
    code, and its value is then the field's subfield mapping rather than a
    string. Building a FieldComparisonResult from it raised two string_type
    errors, which failed the linker and abandoned the record.
    """

    whole_field_diff = {
        "tag": "336",
        "code": None,
        "value_main": {"a": "statický obraz", "b": "sti", "2": "rdacontent"},
        "value_test": {"a": "text", "b": "txt", "2": "rdacontent"},
    }
    monkeypatch.setattr(
        default_comparator,
        "compare_records",
        lambda *args, **kwargs: {"differences": [whole_field_diff], "identical": []},
    )
    monkeypatch.setattr(
        default_comparator,
        "score_differences",
        lambda *args, **kwargs: {
            "record_score_30_exact": 30.0,
            "field_contributions": [],
            "components": [],
        },
    )

    comparator = DefaultComparator(DefaultComparatorConfig())
    result = await comparator.run(marc_record(), marc_record())

    # Reported as nothing rather than as a malformed field: a whole-field diff
    # carries no subfield to explain. Completing at all is the point — this
    # raised before, and the record went unprocessed because of it.
    assert result.field_results == []

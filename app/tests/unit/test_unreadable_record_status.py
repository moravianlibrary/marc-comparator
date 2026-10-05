"""A record that will not parse is not a record that is missing.

`MZK03-001252166` answered 404 while sitting in the catalogue list. Pydantic's
ValidationError subclasses ValueError, so a record whose MARC parsed but failed
the model landed in the same branch as "no such record" and was reported the
same way — sending people to look for something that was never gone.

The record that prompted it reads now: marcdantic 0.3.14 takes the indicator
as catalogued. The classification still matters for whatever is unreadable
next, so both halves are covered here.
"""

from typing import Any, cast

import lxml.etree as etree
import pytest
from marcdantic import MarcRecord
from pydantic import BaseModel, Field, ValidationError

from adapters.marc_sectors import STORED_MARC_CONTEXT, marc_bytes_of, read_stored_marc
from catalog_records import service
from catalog_records.exceptions import (
    CatalogRecordNotFoundException,
    CatalogRecordUnreadableException,
)

NO_SESSION = cast(Any, object())


class _Indicators(BaseModel):
    ind1: str = Field(pattern=r"^[0-9a-z\? ]?$")


def _marc_validation_error() -> ValidationError:
    """A real pydantic error, shaped the way marcdantic's would be."""

    try:
        _Indicators.model_validate({"ind1": "S"})
    except ValidationError as e:
        return e
    raise AssertionError("expected the model to reject 'S'")


class _Record:
    deleted = False

    def __init__(self, raises: Exception):
        self._raises = raises

    def get_record(self, _db):
        raise self._raises


def _patch_lookup(monkeypatch, record):
    monkeypatch.setattr(
        service.CatalogRecord,
        "find_by_base_and_system_number",
        classmethod(lambda cls, db, base, system_number: record),
    )


def test_a_record_that_does_not_validate_is_422_not_404(monkeypatch):
    _patch_lookup(monkeypatch, _Record(_marc_validation_error()))

    with pytest.raises(CatalogRecordUnreadableException) as caught:
        service.get_marc_record("MZK03", "001252166", NO_SESSION)

    assert caught.value.status_code == 422


def test_the_rejected_field_is_named(monkeypatch):
    # Everything needed for a usable message is already in hand at the point of
    # failure; the old branch threw it away.
    _patch_lookup(monkeypatch, _Record(_marc_validation_error()))

    with pytest.raises(CatalogRecordUnreadableException) as caught:
        service.get_marc_record("MZK03", "001252166", NO_SESSION)

    assert "ind1" in caught.value.detail
    assert "MZK03-001252166" in caught.value.detail


def test_unreadable_bytes_are_also_422(monkeypatch):
    # The record row exists either way, so neither case is a 404.
    _patch_lookup(monkeypatch, _Record(ValueError("MARC data not found for MZK03-001252166")))

    with pytest.raises(CatalogRecordUnreadableException) as caught:
        service.get_marc_record("MZK03", "001252166", NO_SESSION)

    assert caught.value.status_code == 422
    assert "MARC data not found" in caught.value.detail


def test_a_record_that_really_is_missing_is_still_404(monkeypatch):
    _patch_lookup(monkeypatch, None)

    with pytest.raises(CatalogRecordNotFoundException) as caught:
        service.get_marc_record("MZK03", "000000000", NO_SESSION)

    assert caught.value.status_code == 404


def test_a_deleted_record_is_still_404(monkeypatch):
    deleted = _Record(AssertionError("should not be read"))
    deleted.deleted = True
    _patch_lookup(monkeypatch, deleted)

    with pytest.raises(CatalogRecordNotFoundException):
        service.get_marc_record("MZK03", "001252166", NO_SESSION)


class TestTheMessageStaysReadable:
    def test_many_errors_are_summarised_rather_than_listed(self):
        class _Strict(BaseModel):
            a: int
            b: int
            c: int
            d: int
            e: int

        with pytest.raises(ValidationError) as caught:
            _Strict.model_validate({})

        described = service._describe_marc_errors(caught.value)

        assert described.count(";") == service._REPORTED_MARC_ERRORS
        assert "and 2 more" in described


class TestTheRecordThatPromptedThisReadsNow:
    """ind1="S" on a 500 is why MZK03-001252166 was unreadable at all.

    marcdantic held indicators to the values MARC 21 defines, so one byte
    outside them lost the whole record — and with it the error, which
    nobody could be told about while the record would not open. 0.3.14
    makes the pattern the caller's to set and defaults to taking the byte
    as catalogued.
    """

    def _marc_with(self, ind1: str) -> bytes:
        namespace = "http://www.loc.gov/MARC21/slim"
        return marc_bytes_of(
            MarcRecord.from_xml(
                etree.fromstring(
                    f'<record xmlns="{namespace}">'
                    "<leader>00000nam a2200000 a 4500</leader>"
                    '<controlfield tag="001">001252166</controlfield>'
                    f'<datafield tag="500" ind1="{ind1}" ind2=" ">'
                    '<subfield code="a">A note</subfield>'
                    "</datafield>"
                    "</record>".encode()
                ),
                STORED_MARC_CONTEXT,
            )
        )

    def test_an_indicator_outside_the_standard_is_read_back_as_catalogued(self):
        record = read_stored_marc(self._marc_with("S"))

        assert record.variable_fields.root["500"][0].ind1 == "S"

    def test_a_record_the_standard_does_define_is_unaffected(self):
        record = read_stored_marc(self._marc_with("1"))

        assert record.variable_fields.root["500"][0].ind1 == "1"

"""A conflicting identifier has to beat an agreeing one.

Measured over 47,777 accepted links: 90 carried a conflicting identifier and
78 of those agreed on a *different* one — retrieved by a matching OCLC or
ISBN, with the national bibliography number saying the two were different
works. Reading them by hand, the ČNB was right every time. So this cannot be
a weight: averaged against several agreements a veto disappears, which is
precisely how a confident wrong link is made.
"""

from marc_comparator.authority_linkers import IdentityConflict, find_identity_conflicts
from marcdantic import MarcRecord


def record(
    *,
    leader: str = "00000nam a2200000 a 4500",
    year: str = "2012",
    nbn: list[str] | None = None,
    isbn: str | None = None,
) -> MarcRecord:
    variable: dict = {}
    if nbn is not None:
        variable["015"] = [{"ind1": " ", "ind2": " ", "subfields": {"a": nbn}}]
    if isbn is not None:
        variable["020"] = [{"ind1": " ", "ind2": " ", "subfields": {"a": [isbn]}}]
    return MarcRecord.model_validate(
        {
            "leader": leader,
            "fixed_fields": {
                "001": "000000001",
                "005": "20200101000000.0",
                "008": f"120529s{year}    xr            000 0 cze d",
            },
            "variable_fields": variable,
        }
    )


class TestTheNationalBibliographyNumberIsAuthoritative:
    def test_disjoint_numbers_are_a_conflict(self):
        ours = record(nbn=["cnb000060633"])
        theirs = record(nbn=["cnb000036811"])

        assert find_identity_conflicts(ours, theirs) == [IdentityConflict.Nbn]

    def test_a_shared_number_among_several_is_agreement(self):
        ours = record(nbn=["cnb000060633", "cnb000099999"])
        theirs = record(nbn=["cnb000099999"])

        assert find_identity_conflicts(ours, theirs) == []

    def test_punctuation_is_not_a_disagreement(self):
        assert (
            find_identity_conflicts(record(nbn=["cnb 000060633"]), record(nbn=["cnb000060633"]))
            == []
        )

    def test_a_record_that_says_nothing_has_not_disagreed(self):
        """Otherwise a sparsely catalogued record is refused for being sparse."""

        assert find_identity_conflicts(record(nbn=["cnb000060633"]), record()) == []
        assert find_identity_conflicts(record(), record(nbn=["cnb000060633"])) == []


class TestTheYearSeparatesEditions:
    def test_years_far_apart_are_a_conflict(self):
        assert find_identity_conflicts(record(year="1990"), record(year="1987")) == [
            IdentityConflict.Year
        ]

    def test_off_by_one_is_cataloguing_variance(self):
        """131 links of 47,777 differ by one; 304 differ by more. Different populations."""

        assert find_identity_conflicts(record(year="1990"), record(year="1991")) == []

    def test_an_unreadable_year_is_not_a_disagreement(self):
        assert find_identity_conflicts(record(year="19uu"), record(year="1987")) == []


class TestTheLeaderSeparatesKindsOfThing:
    def test_a_different_record_type_is_a_conflict(self):
        ours = record(leader="00000nam a2200000 a 4500")
        theirs = record(leader="00000njm a2200000 a 4500")

        assert find_identity_conflicts(ours, theirs) == [IdentityConflict.RecordType]

    def test_a_monograph_is_not_a_serial(self):
        ours = record(leader="00000nam a2200000 a 4500")
        theirs = record(leader="00000nas a2200000 a 4500")

        assert find_identity_conflicts(ours, theirs) == [IdentityConflict.BibliographicLevel]

    def test_an_unset_leader_position_is_not_a_kind(self):
        """Records reach us with these blank; blank must not conflict with everything."""

        ours = record(leader="00000n   a2200000 a 4500")
        theirs = record(leader="00000nam a2200000 a 4500")

        assert find_identity_conflicts(ours, theirs) == []


class TestWhatIsDeliberatelyNotAConflict:
    def test_a_differing_isbn_is_not_enough(self):
        """Manifestation-level and routinely borrowed across editions, unlike ČNB."""

        assert find_identity_conflicts(record(isbn="8071781150"), record(isbn="8071781169")) == []

    def test_identical_records_conflict_over_nothing(self):
        assert find_identity_conflicts(record(nbn=["cnb1"]), record(nbn=["cnb1"])) == []


def test_every_reason_is_reported_not_just_the_first():
    """The row shows why it was refused, and one cause is rarely the whole story."""

    ours = record(leader="00000nam a2200000 a 4500", year="1990", nbn=["cnb000060633"])
    theirs = record(leader="00000nas a2200000 a 4500", year="1975", nbn=["cnb000036811"])

    assert find_identity_conflicts(ours, theirs) == [
        IdentityConflict.Nbn,
        IdentityConflict.Year,
        IdentityConflict.BibliographicLevel,
    ]

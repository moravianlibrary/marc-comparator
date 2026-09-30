"""Evidence that two records cannot be the same work.

Separate from the comparator on purpose. The comparator answers how much two
records agree; this answers whether they describe the same thing at all, and
the two are different questions. A pair both catalogues give the same ISBN
scores low when they describe the same book very differently — a finding, not
a bad link — while two different editions can agree on almost everything.

Measured over all 47,777 accepted links in the local database, every signal
here fires below 0.80 confidence, so none of them reaches a link a confidence
floor would miss. They are worth having for precision rather than reach: a
floor at 0.80 removes 20,865 links to catch the ~470 these find, while these
remove the ~470.

**They gate, they do not score.** Of the 90 links with a conflicting
identifier, 78 agree on a *different* one — retrieved by a matching OCLC or
ISBN, with the national bibliography number saying the two are different
works, and the national bibliography number right in every case read by hand.
A veto averaged in against several agreements disappears, which is exactly how
a confident wrong link is produced.
"""

from __future__ import annotations

import re
from enum import StrEnum

from marcdantic import MarcRecord
from marcdantic.selectors import NbnActiveJq

#: Fixed-length data elements, holding the publication year at 07-10.
CONTROL_FIELD_008 = "008"

#: How far two publication years may drift before it means anything.
#:
#: Off by one is ordinary cataloguing variance — 131 links of 47,777, against
#: 304 that differ by more — and the two populations look completely different
#: when read. A year in a record is the year somebody typed, not a fact.
YEAR_TOLERANCE = 1


class IdentityConflict(StrEnum):
    """Why two records cannot be the same work.

    Stored as strings on the link row, so these values are data: renaming one
    orphans the rows already carrying it.
    """

    #: Both records carry a national bibliography number and they are disjoint.
    #: ČNB is assigned per bibliographic unit by the national library, which is
    #: what makes a disagreement authoritative rather than merely suspicious.
    Nbn = "nbn"

    #: Publication years more than ``YEAR_TOLERANCE`` apart. Usually a link
    #: between two editions of the same title.
    Year = "year"

    #: Leader/06. A score cannot see the difference between a book and a sound
    #: recording that were catalogued alike.
    RecordType = "record-type"

    #: Leader/07. A monograph linked to a serial.
    BibliographicLevel = "bibliographic-level"


#: Conflicts deliberately not in the list above.
#:
#: **UUID** (12 links, 3 of them at 0.95+ with matching years). UUIDs are read
#: out of 856 ``$u``, where the identifier pollution already known to produce
#: bad 856 batches lives, and two records for one book legitimately point at
#: different digitisations. It is not evidence.
#:
#: **ISBN, OCLC and ISSN** (24 links between them). Unlike ČNB these are
#: manifestation-level and routinely duplicated or borrowed across editions, so
#: a disagreement is weak where a ČNB disagreement is not. Small enough to add
#: later if the ČNB rule proves out; not worth the false positives now.
_REJECTED_SIGNALS = ("uuid", "isbn", "oclc", "issn")


def normalize_identifier(value: str) -> str | None:
    """Reduce an identifier to the characters that carry it."""

    normalized = re.sub(r"[^\w]", "", value).lower()
    return normalized or None


def year_from_008(field: str | None) -> int | None:
    """Date 1 from the fixed-length data elements, when it is a plain year."""

    if field is None or len(field) < 11:
        return None
    candidate = field[7:11]
    return int(candidate) if candidate.isdigit() else None


def _nbns(record: MarcRecord) -> set[str]:
    found = set()
    for raw in record.variable_fields.query(NbnActiveJq) or []:
        normalized = normalize_identifier(raw)
        if normalized:
            found.add(normalized)
    return found


def _leader_position(record: MarcRecord, position: int) -> str | None:
    """One leader byte, or None where the record does not state it.

    Blank is not a value. Records reach us with an unset leader/06 and /07, and
    reading blank as a distinct type would make every such record conflict with
    every properly coded one.
    """

    leader = record.leader
    if len(leader) <= position:
        return None
    char = leader[position]
    return char if char.strip() else None


def find_identity_conflicts(ours: MarcRecord, theirs: MarcRecord) -> list[IdentityConflict]:
    """Every reason these two records cannot describe the same work.

    Each test needs the fact present on *both* sides. A record that does not
    say something has not disagreed with one that does — asymmetry here would
    reject candidates for being sparsely catalogued, which is the opposite of
    what this is for.
    """

    conflicts: list[IdentityConflict] = []

    our_nbns, their_nbns = _nbns(ours), _nbns(theirs)
    if our_nbns and their_nbns and not (our_nbns & their_nbns):
        conflicts.append(IdentityConflict.Nbn)

    our_year = year_from_008(ours.fixed_fields.root.get(CONTROL_FIELD_008))
    their_year = year_from_008(theirs.fixed_fields.root.get(CONTROL_FIELD_008))
    if (
        our_year is not None
        and their_year is not None
        and abs(our_year - their_year) > YEAR_TOLERANCE
    ):
        conflicts.append(IdentityConflict.Year)

    for position, conflict in (
        (6, IdentityConflict.RecordType),
        (7, IdentityConflict.BibliographicLevel),
    ):
        our_code = _leader_position(ours, position)
        their_code = _leader_position(theirs, position)
        if our_code is not None and their_code is not None and our_code != their_code:
            conflicts.append(conflict)

    return conflicts

"""rename foreign_digital_library and send volume links to review

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-10-15 18:00:00.000000

`foreign_digital_library` described 408 of its 11,991 findings. The rest are
not another institution's digital library: 5,822 point at MZK's own image
server and 1,569 at its map viewer, and most of the remainder are Google
Books, MDZ, Manuscriptorium and the like. The bucket is "a digitised copy
that is not in our Kramerius", so it is named for that.

`non_top_level_document` stops being an error with a known fix. Pointing the
link at the top of its hierarchy was right for the 21 page links and wrong
for the 361 others: 179 name a monograph unit, 83 an issue, 6 a volume, and
136 sit on a field carrying a `$z` volume designation. Rewriting those
discarded the object a cataloguer deliberately chose, and where several
volumes shared one parent it left the record holding the same link twice
under different labels — in one case with `$z Díl 2/1` pointing at the object
`$z Díl 3/1` names. It is reported for a person now, so it is ForReview.

Status is a pure function of the reason, so re-deriving it here is one
UPDATE rather than a re-validation of 340,634 records.

`catalog_records_analytics` and the facet cube hold copies of both fields and
are rebuilt from `validations` by the usual analytics task, not here.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VALIDATOR = "kramerius-links"

RENAMES = {"foreign_digital_library": "other_online_resource"}

#: Mirrors `REASON_STATUS` in the validator. Kept literal rather than imported
#: so a later edit to the validator cannot silently rewrite history here.
STATUSES = {
    "no_links_found_or_expected": "Valid",
    "valid_link": "Valid",
    "missing_link_in_marc": "Invalid",
    "link_not_found": "Invalid",
    "non_canonical_url_not_found": "Invalid",
    "non_canonical_url_found": "ForReview",
    "missing_link_text": "ForReview",
    "identifier_matches_multiple_documents": "ForReview",
    "non_linkable_model": "ForReview",
    "invalid_link_format": "ForReview",
    "non_top_level_document": "ForReview",
    "other_online_resource": "AdditionalInfo",
}

#: The same table as it stood before this revision, written out rather than
#: derived from the one above, for the same reason that one is literal.
OLD_STATUSES = {
    "no_links_found_or_expected": "Valid",
    "valid_link": "Valid",
    "missing_link_in_marc": "Invalid",
    "link_not_found": "Invalid",
    "non_canonical_url_not_found": "Invalid",
    "non_top_level_document": "Invalid",
    "non_canonical_url_found": "ForReview",
    "missing_link_text": "ForReview",
    "identifier_matches_multiple_documents": "ForReview",
    "non_linkable_model": "ForReview",
    "invalid_link_format": "ForReview",
    "foreign_digital_library": "AdditionalInfo",
}


def _apply(mapping: dict[str, str], column: str) -> None:
    """Set `result[column]` from the row's own reason, in one statement."""

    pairs = ", ".join(f"('{reason}', '{value}')" for reason, value in mapping.items())
    op.execute(
        f"""
        UPDATE validations AS v
        SET result = jsonb_set(v.result, '{{{column}}}', to_jsonb(m.value))
        FROM (VALUES {pairs}) AS m(reason, value)
        WHERE v.validator = '{VALIDATOR}'
          AND v.result->>'reason' = m.reason
          AND v.result->>'{column}' IS DISTINCT FROM m.value
        """
    )


def upgrade() -> None:
    _apply(RENAMES, "reason")
    _apply(STATUSES, "status")


def downgrade() -> None:
    _apply({new: old for old, new in RENAMES.items()}, "reason")
    _apply(OLD_STATUSES, "status")

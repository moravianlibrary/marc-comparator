"""regrade kramerius-links findings and merge the non-canonical URL reasons

Revision ID: a1b2c3d4e5f6
Revises: e7f8a9b0c1d2
Create Date: 2026-10-13 14:00:00.000000

The validator used to grade a finding by what was wrong with the URL: a
non-standard path was an observation, the legacy host an error. A reader
could not tell the two apart and the repair was identical, so they are now
one pair of reasons graded by whether the document is actually there.

Status is a pure function of the reason, which is what makes this a data
migration rather than a re-validation: re-deriving it here costs one UPDATE,
while re-running the validator over 282k records would mean as many Kramerius
lookups.

The malformed PIDs are the exception that cannot be re-derived. A loose URL
pattern read `uuid:...827e52D` and `uuid:29ac5300-...-005056827e` — one with
a stray character, one truncated — as documents, failed to find them, and
filed them as `link_not_found`, which under the new repair rules removes the
856. The URL they came from is not stored, so the pattern change alone cannot
reclassify them; they are identifiable by the PID itself and are moved here,
before any report can act on them.

`catalog_records_analytics` and the facet cube carry copies of the status and
are rebuilt from `validations` afterwards, so both are refreshed by the usual
analytics task rather than here.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VALIDATOR = "kramerius-links"

#: The reason each retired one becomes. Path and host stopped being different
#: findings; only found-versus-not-found still is.
RENAMES = {
    "wrong_path_found": "non_canonical_url_found",
    "wrong_server_found": "non_canonical_url_found",
    "wrong_path_not_found": "non_canonical_url_not_found",
    "wrong_server_not_found": "non_canonical_url_not_found",
}

#: Mirrors `REASON_STATUS` in the validator. Kept literal rather than imported
#: so a later edit to the validator cannot silently rewrite history here.
STATUSES = {
    "no_links_found_or_expected": "Valid",
    "valid_link": "Valid",
    "missing_link_in_marc": "Invalid",
    "non_top_level_document": "Invalid",
    "link_not_found": "Invalid",
    "non_canonical_url_not_found": "Invalid",
    "non_canonical_url_found": "ForReview",
    "missing_link_text": "ForReview",
    "identifier_matches_multiple_documents": "ForReview",
    "non_linkable_model": "ForReview",
    "invalid_link_format": "ForReview",
    "foreign_digital_library": "AdditionalInfo",
}

#: What the validator now accepts as a PID.
CANONICAL_PID = (
    r"^uuid:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

#: Statuses as they were set at each call site before the table existed.
OLD_STATUSES = {
    "wrong_path_found": "AdditionalInfo",
    "wrong_path_not_found": "AdditionalInfo",
    "wrong_server_found": "Invalid",
    "wrong_server_not_found": "Invalid",
    "missing_link_text": "ForReview",
    "identifier_matches_multiple_documents": "ForReview",
    "non_linkable_model": "AdditionalInfo",
    "foreign_digital_library": "AdditionalInfo",
    "invalid_link_format": "Invalid",
    "no_links_found_or_expected": "Valid",
    "valid_link": "Valid",
    "missing_link_in_marc": "Invalid",
    "non_top_level_document": "Invalid",
    "link_not_found": "Invalid",
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
    # A typo is a URL we cannot read, not a document that has gone missing.
    # Done before the renames so the rows are still findable by their reason.
    op.execute(
        f"""
        UPDATE validations
        SET result = jsonb_set(result, '{{reason}}', '"invalid_link_format"')
        WHERE validator = '{VALIDATOR}'
          AND result->>'reason' = 'link_not_found'
          AND result->'params'->>'pid' !~ '{CANONICAL_PID}'
        """
    )
    _apply(RENAMES, "reason")
    _apply(STATUSES, "status")


def downgrade() -> None:
    # The merged reasons cannot be told apart again — path and host are not
    # recorded anywhere else — so every one goes back as the path flavour,
    # which is what all but three of them were.
    op.execute(
        f"""
        UPDATE validations
        SET result = jsonb_set(
            result, '{{reason}}',
            to_jsonb(replace(result->>'reason', 'non_canonical_url', 'wrong_path'))
        )
        WHERE validator = '{VALIDATOR}'
          AND result->>'reason' LIKE 'non_canonical_url%'
        """
    )
    _apply(OLD_STATUSES, "status")

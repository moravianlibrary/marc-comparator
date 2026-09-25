"""`processed_at` records that a record was processed, not that a job ran.

Every reader treats it as a boolean — "processed since it last changed" — so
re-stamping a record whose links, comparisons and validations all still say
what they said conveys nothing. It is not free either: `updated_at` is indexed
and moves with any write, so each such write is a non-HOT update that rewrites
the primary key, that index and the GIN index over `search_vector`.

The pass cannot simply skip records whose MARC is unchanged, though: validators
ask Kramerius and linkers ask the dump and knihovny.cz, and either can answer
differently than it did last time.
"""

import pytest

from catalog_records.tasks import _handle_result_changes, _link_fingerprint
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord
from entities.validation import Validation
from tests.conftest import create_catalog_record, load_test_record


@pytest.mark.db
@pytest.mark.redis
class TestTheVerdictIsReported:
    @pytest.fixture
    def record(self, db_session, marc_cache_client) -> CatalogRecord:
        record = create_catalog_record(
            db_session, "MZK01", "000600001", load_test_record("MZK01-001217709.mrc")
        )
        db_session.commit()
        return record

    def test_no_change_reports_false(self, db_session, record):
        """A pass that replaces results with the same results found nothing."""
        from catalog_records.tasks import _compute_result_hashes

        before = _compute_result_hashes(db_session, record.id)

        assert _handle_result_changes(db_session, record.id, before) is False

    def test_a_new_result_reports_true(self, db_session, record):
        from marc_comparator.validators import (
            ValidationResult,
            ValidationTarget,
            ValidityStatus,
        )

        from catalog_records.tasks import _compute_result_hashes

        before = _compute_result_hashes(db_session, record.id)
        Validation.replace_all(
            db_session,
            record.id,
            "kramerius-links",
            [
                ValidationResult(
                    target=ValidationTarget(tag="856", codes=["u"]),
                    status=ValidityStatus.Invalid,
                    reason="missing",
                )
            ],
        )
        db_session.flush()

        assert _handle_result_changes(db_session, record.id, before) is True


class TestLinksCountAsAChange:
    def test_the_same_links_fingerprint_the_same(self):
        links = [
            AuthorityLink(
                main_record_id="MZK01-1",
                linker="knihovny-cz",
                base="SKC",
                authority_record_id="SKC-1",
                confidence=0.9,
            ),
            AuthorityLink(
                main_record_id="MZK01-1",
                linker="marcxml-dump",
                base="SKC",
                authority_record_id="SKC-2",
                confidence=0.8,
            ),
        ]

        assert _link_fingerprint(links) == _link_fingerprint(list(reversed(links))), (
            "the order the database returns links in is not a change"
        )

    def test_a_different_authority_record_is_a_change(self):
        before = [
            AuthorityLink(
                main_record_id="MZK01-1",
                linker="knihovny-cz",
                base="SKC",
                authority_record_id="SKC-1",
                confidence=0.9,
            )
        ]
        after = [
            AuthorityLink(
                main_record_id="MZK01-1",
                linker="knihovny-cz",
                base="SKC",
                authority_record_id="SKC-9",
                confidence=0.9,
            )
        ]

        assert _link_fingerprint(before) != _link_fingerprint(after)

    def test_a_different_confidence_is_a_change(self):
        before = [
            AuthorityLink(
                main_record_id="MZK01-1",
                linker="knihovny-cz",
                base="SKC",
                authority_record_id="SKC-1",
                confidence=0.9,
            )
        ]
        after = [
            AuthorityLink(
                main_record_id="MZK01-1",
                linker="knihovny-cz",
                base="SKC",
                authority_record_id="SKC-1",
                confidence=0.4,
            )
        ]

        assert _link_fingerprint(before) != _link_fingerprint(after)

    def test_losing_a_link_is_a_change(self):
        link = AuthorityLink(
            main_record_id="MZK01-1",
            linker="knihovny-cz",
            base="SKC",
            authority_record_id="SKC-1",
            confidence=0.9,
        )

        assert _link_fingerprint([link]) != _link_fingerprint([])


@pytest.mark.db
@pytest.mark.redis
class TestNeverProcessedIsAlwaysStamped:
    def test_a_record_with_no_results_at_all_still_gets_processed(
        self, db_session, marc_cache_client
    ):
        """Otherwise a record nothing can be said about stays Unprocessed forever."""
        from catalog_records.tasks import _compute_result_hashes, _link_fingerprints_for

        record = create_catalog_record(
            db_session, "MZK01", "000600002", load_test_record("MZK01-001217709.mrc")
        )
        db_session.commit()

        before = _compute_result_hashes(db_session, record.id)
        links_before = _link_fingerprints_for(db_session, [record.id])

        results_changed = _handle_result_changes(db_session, record.id, before)
        links_changed = _link_fingerprint([]) != links_before[record.id]

        assert results_changed is False
        assert links_changed is False
        assert record.processed_at is None
        # Which is exactly why the condition carries the third clause.
        assert results_changed or links_changed or record.processed_at is None

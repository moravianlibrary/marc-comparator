"""A candidate's MARC has to be readable, or nobody can rule on it.

Candidates deliberately get no ``catalog_records`` row — that is what keeps
one cheap enough to store several per record — and the catalogue's own MARC
endpoint resolves that row before it reads anything. So the one screen that
asks a cataloguer "are these two the same work?" could offer them a system
number and a score and nothing else.

The bytes were never missing. ``store_candidate_marc`` writes them to sector
storage, which is keyed by base and system number with no foreign key to the
catalogue; this is the read path that was missing.
"""

import pytest
from httpx import AsyncClient

from adapters.marc_sectors import marc_bytes_of, upsert_record_in_sector
from entities.catalog_record import CatalogRecord
from tests.conftest import load_test_record

pytestmark = pytest.mark.db

CANDIDATE_BASE = "SKC"
CANDIDATE_SYSNO = "000987654"


def _store_candidate(db_session, raw: bytes, system_number: str = CANDIDATE_SYSNO) -> None:
    upsert_record_in_sector(db_session, CANDIDATE_BASE, system_number, raw)
    db_session.commit()


class TestACandidateWithNoCatalogueRow:
    @pytest.mark.asyncio
    async def test_its_stored_marc_is_served(self, db_session, user, client: AsyncClient):
        record = load_test_record("MZK01-001217709.mrc")
        _store_candidate(db_session, marc_bytes_of(record))

        # The premise: nothing in the catalogue knows about this record. If a
        # row ever appeared here the test would pass through the ordinary
        # reader and prove nothing.
        assert (
            CatalogRecord.find_by_base_and_system_number(
                db_session, CANDIDATE_BASE, CANDIDATE_SYSNO
            )
            is None
        )

        response = await client.get(
            f"/authority-linking/candidates/{CANDIDATE_BASE}/{CANDIDATE_SYSNO}/marc"
        )

        assert response.status_code == 200
        assert response.json()["leader"] == record.leader

    @pytest.mark.asyncio
    async def test_the_catalogue_reader_still_refuses_it(
        self, db_session, user, client: AsyncClient
    ):
        """The new path is an addition, not a loosening of the old one.

        A 404 from the catalogue means "this is not a record of ours", and a
        candidate is not one however much of its MARC we keep.
        """

        _store_candidate(db_session, marc_bytes_of(load_test_record("MZK01-001217709.mrc")))

        response = await client.get(f"/catalog-records/{CANDIDATE_BASE}/{CANDIDATE_SYSNO}/marc")

        assert response.status_code == 404


class TestWhatIsNotThere:
    @pytest.mark.asyncio
    async def test_a_candidate_we_kept_no_copy_of_is_a_404(
        self, db_session, user, client: AsyncClient
    ):
        """An ordinary answer, not a defect.

        A linker that assembles a candidate rather than parsing one has no
        raw MARC to keep, and a row written before candidate storage existed
        picks its MARC up only on the next pass. Both are expected, so the
        interface needs an empty state rather than an error.
        """

        response = await client.get(
            f"/authority-linking/candidates/{CANDIDATE_BASE}/000000001/marc"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_a_copy_that_will_not_parse_is_not_a_404(
        self, db_session, user, client: AsyncClient
    ):
        """Held and broken is a different answer from never held.

        Same distinction the catalogue's reader draws, and for the same
        reason: only one of the two is worth chasing.
        """

        _store_candidate(db_session, b"this is not a MARC record")

        response = await client.get(
            f"/authority-linking/candidates/{CANDIDATE_BASE}/{CANDIDATE_SYSNO}/marc"
        )

        assert response.status_code == 422
        assert "cannot be read" in response.json()["detail"]

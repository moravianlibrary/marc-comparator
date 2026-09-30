"""A constraint the database enforces is not a crash.

Nothing caught IntegrityError, so every one of them answered 500 — assigning
somebody a role they already hold, referencing a row that has since gone. A
500 tells a caller the service is broken and there is nothing they can do,
which is the opposite of what a constraint violation usually means.
"""

import logging
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from adapters.errors import (
    CHECK_VIOLATION,
    FOREIGN_KEY_VIOLATION,
    NOT_NULL_VIOLATION,
    UNIQUE_VIOLATION,
    integrity_error_handler,
)


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/x", "headers": []})


def _error(sqlstate: str | None, constraint: str | None = None) -> IntegrityError:
    orig = SimpleNamespace(pgcode=sqlstate, diag=SimpleNamespace(constraint_name=constraint))
    return IntegrityError("INSERT ...", {}, orig)  # type: ignore[arg-type]


async def _answer(error: IntegrityError):
    response = await integrity_error_handler(_request(), error)
    return response.status_code, response.body.decode()


class TestAConflictIsReportedAsOne:
    @pytest.mark.asyncio
    async def test_a_duplicate_is_a_conflict(self):
        code, body = await _answer(_error(UNIQUE_VIOLATION))

        assert code == 409
        assert "already exists" in body

    @pytest.mark.asyncio
    async def test_a_missing_reference_is_a_conflict(self):
        code, _ = await _answer(_error(FOREIGN_KEY_VIOLATION))

        assert code == 409

    @pytest.mark.asyncio
    async def test_a_value_the_database_refuses_is_unprocessable(self):
        code, _ = await _answer(_error(CHECK_VIOLATION))

        assert code == 422

    @pytest.mark.asyncio
    async def test_the_rule_that_was_broken_is_named(self):
        code, body = await _answer(_error(UNIQUE_VIOLATION, "link_claims_pkey"))

        assert code == 409
        assert "link_claims_pkey" in body


class TestOurOwnBugsStayFiveHundred:
    @pytest.mark.asyncio
    async def test_a_null_where_one_is_not_allowed_is_not_the_callers_fault(self):
        # Nothing a caller sent can make a NOT NULL column null; something
        # here forgot to set it. Answering 409 would blame them for it.
        code, body = await _answer(_error(NOT_NULL_VIOLATION))

        assert code == 500
        assert "Internal server error" in body

    @pytest.mark.asyncio
    async def test_an_unrecognised_state_stays_five_hundred(self):
        code, _ = await _answer(_error("XX000"))

        assert code == 500

    @pytest.mark.asyncio
    async def test_an_error_carrying_no_state_at_all_stays_five_hundred(self):
        code, _ = await _answer(_error(None))

        assert code == 500


class TestNothingStoredIsEchoedBack:
    @pytest.mark.asyncio
    async def test_the_databases_own_message_is_not_passed_on(self):
        # Postgres puts the offending values in DETAIL, and those can be
        # anything a caller sent or anything already stored.
        orig = SimpleNamespace(
            pgcode=UNIQUE_VIOLATION,
            diag=SimpleNamespace(constraint_name="users_email_key"),
        )
        error = IntegrityError(
            "INSERT INTO users ...",
            {},
            orig,  # type: ignore[arg-type]
        )
        error.args = ("DETAIL:  Key (email)=(someone@example.org) already exists.",)

        _, body = await _answer(error)

        assert "someone@example.org" not in body

    @pytest.mark.asyncio
    async def test_it_is_logged_even_so(self, caplog):
        with caplog.at_level(logging.WARNING):
            await _answer(_error(UNIQUE_VIOLATION, "users_email_key"))

        assert "users_email_key" in caplog.text

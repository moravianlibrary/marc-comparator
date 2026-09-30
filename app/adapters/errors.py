"""What the API answers when the database refuses a write.

Nothing caught ``IntegrityError``, so every constraint the database enforces
answered **500**: assigning somebody a role they already hold, claiming a
record twice, referencing a row that has since gone. A 500 says "this service
is broken and there is nothing you can do"; a constraint violation usually
says the opposite — the request conflicts with what is already stored, and the
caller can tell that from the answer and act on it.

The mapping is by SQLSTATE rather than by message, because messages are
localized and change between server versions.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

#: SQLSTATE classes worth telling the caller apart, and what each one means
#: for the request that provoked it.
UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"
NOT_NULL_VIOLATION = "23502"
CHECK_VIOLATION = "23514"
EXCLUSION_VIOLATION = "23P01"

_STATUS_BY_SQLSTATE = {
    #: The row is already there. Not a failure of the service.
    UNIQUE_VIOLATION: status.HTTP_409_CONFLICT,
    #: Something the request names does not exist, or is still referenced by
    #: something that does. Either way the conflict is with stored state.
    FOREIGN_KEY_VIOLATION: status.HTTP_409_CONFLICT,
    EXCLUSION_VIOLATION: status.HTTP_409_CONFLICT,
    #: A value the request supplied is not one the database will accept.
    CHECK_VIOLATION: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

_DETAIL_BY_SQLSTATE = {
    UNIQUE_VIOLATION: "That already exists.",
    FOREIGN_KEY_VIOLATION: "That refers to something which does not exist, or is still in use.",
    EXCLUSION_VIOLATION: "That conflicts with something already stored.",
    CHECK_VIOLATION: "One of the values is not allowed here.",
}


def _sqlstate(error: IntegrityError) -> str | None:
    return getattr(error.orig, "pgcode", None)


def _constraint(error: IntegrityError) -> str | None:
    """The constraint's name, which is the one safe thing to pass on.

    The database's own message carries a DETAIL line quoting the offending
    values, and those can be anything a caller sent or anything already
    stored. The name says which rule was broken without repeating data.
    """

    diagnostics = getattr(error.orig, "diag", None)
    return getattr(diagnostics, "constraint_name", None)


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Answer a constraint violation as a conflict rather than a crash."""

    error = exc if isinstance(exc, IntegrityError) else None
    sqlstate = _sqlstate(error) if error is not None else None
    code = _STATUS_BY_SQLSTATE.get(sqlstate or "")

    if code is None:
        # A NOT NULL violation, or something unrecognised. The caller did not
        # cause this and cannot fix it, so it stays a 500 and keeps the
        # traceback — the whole point of the mapping above is that these two
        # cases are different.
        logger.exception("Unhandled database constraint on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )

    constraint = _constraint(error) if error is not None else None
    logger.warning(
        "%s %s violated %s (%s)",
        request.method,
        request.url.path,
        constraint or "a constraint",
        sqlstate,
    )

    detail = _DETAIL_BY_SQLSTATE.get(sqlstate or "", "That conflicts with what is stored.")
    content: dict[str, str] = {"detail": detail}
    if constraint:
        content["constraint"] = constraint
    return JSONResponse(status_code=code, content=content)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, integrity_error_handler)

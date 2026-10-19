from fastapi import HTTPException, status


class CandidateMarcNotStoredException(HTTPException):
    """We hold no copy of this candidate's MARC.

    Not the same as "no such record", and the difference matters to whoever
    is looking at it. The candidate is real — a linker proposed it and a row
    names it — we simply never kept the bytes. Two ways that happens, both
    ordinary: a linker that assembles a candidate rather than parsing one has
    no raw MARC to keep (``store_candidate_marc`` says so and moves on), and
    a candidate row written before that storage existed picks its MARC up on
    the next linking pass.
    """

    def __init__(self, base: str, system_number: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored MARC for candidate {base}-{system_number}.",
        )


class CandidateMarcUnreadableException(HTTPException):
    """We hold a copy and it will not parse.

    Separate from the above for the same reason the catalogue's two read
    errors are separate: one says there is nothing to show, the other says
    there is something wrong with what we kept, and only the second is a
    defect worth chasing.
    """

    def __init__(self, base: str, system_number: str, reason: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Stored MARC for candidate {base}-{system_number} cannot be read: {reason}",
        )


class ComparatorUnavailableException(HTTPException):
    """Nothing is configured to compare with.

    Either the comparison settings row is absent or what it stores will not
    construct. Both are an operator's problem rather than the caller's, which
    is why this is a 503 and not a 400: the request was well formed, the
    service is not in a state to answer it.
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No comparator is configured, so candidates cannot be compared.",
        )

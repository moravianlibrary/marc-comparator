from fastapi import HTTPException, status


class CatalogRecordNotFoundException(HTTPException):
    def __init__(self, base: str, system_number: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog record {base}-{system_number} not found.",
        )


class CatalogRecordUnreadableException(HTTPException):
    """The record is in the catalogue; what is stored under it will not parse.

    Separate from "not found" because the two send someone to different places.
    A 404 says the record is not here, and for a record sitting in the list with
    a system number the caller just clicked, that is simply false — it sent
    people looking for a record that was never missing. This says the record is
    here and its stored MARC is the problem, and names the field.
    """

    def __init__(self, base: str, system_number: str, reason: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Catalog record {base}-{system_number} cannot be read: {reason}",
        )


class SyncTaskAlreadyRunningException(HTTPException):
    def __init__(self, base: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sync task is already running for base {base}.",
        )

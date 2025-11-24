from fastapi import HTTPException, status


class CatalogRecordNotFoundException(HTTPException):
    def __init__(self, base: str, system_number: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog record {base}-{system_number} not found.",
        )


class SyncTaskAlreadyRunningException(HTTPException):
    def __init__(self, base: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sync task is already running for base {base}.",
        )

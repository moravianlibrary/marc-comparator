from fastapi import HTTPException, status


class ImmutableRoleModificationException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an immutable role",
        )


class ProtectedRoleRenameException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rename a protected role",
        )


class ImmutableRoleDeletionException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an immutable role",
        )


class ProtectedRoleDeletionException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a protected role",
        )

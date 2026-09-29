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


class SystemUserRoleModificationException(HTTPException):
    """The scheduler's own account is not an account anyone administers.

    Every periodic task runs on its behalf, so taking Admin away from it stops
    scheduled work having permission to do anything until the next restart puts
    the role back. Startup repairs that, which makes the damage temporary and
    silent rather than survivable.
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change the roles of the system user",
        )

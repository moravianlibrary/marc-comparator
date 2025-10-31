from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status

from adapters.database import DatabaseSession, db_session_generator
from adapters.indexer import IndexerSession, get_indexer_session
from auth.service import CurrentUser, get_current_user_data
from entities.role import Permission

DatabaseSessionDep = Annotated[DatabaseSession, Depends(db_session_generator)]
IndexerSessionDep = Annotated[IndexerSession, Depends(get_indexer_session)]


class PermissionDenied(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )


def require_permission(
    permission: Permission,
    exception: HTTPException = PermissionDenied(),
) -> Callable:
    def _check_permissions(user: CurrentUser, db_session: DatabaseSessionDep):
        user_data = get_current_user_data(user, db_session)
        if permission not in user_data.permissions:
            raise exception

    return Depends(_check_permissions)


WithPermission = require_permission

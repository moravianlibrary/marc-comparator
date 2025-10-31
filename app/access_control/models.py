from typing import List

from pydantic import BaseModel

from common.models import PageRequestParams
from entities.role import Permission


class EditRole(BaseModel):
    name: str
    permissions: List[Permission]


class RoleSchema(EditRole):
    id: int
    immutable: bool
    protected: bool


class UsersRequestParams(PageRequestParams):
    email: str | None = None

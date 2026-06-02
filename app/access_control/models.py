from pydantic import BaseModel

from common.models import PageRequestParams
from entities.role import Permission


class EditRole(BaseModel):
    name: str
    permissions: list[Permission]


class RoleSchema(EditRole):
    id: int
    immutable: bool
    protected: bool


class RoleSummary(BaseModel):
    id: int
    name: str


class UsersRequestParams(PageRequestParams):
    email: str | None = None

from typing import List
from uuid import UUID

from pydantic import BaseModel, EmailStr

from access_control.models import RoleSummary
from entities.role import Permission


class RegisterUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str | None = None


class UserSchema(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    roles: List[RoleSummary]


class MeSchema(UserSchema):
    permissions: List[Permission]

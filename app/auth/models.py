from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from access_control.models import RoleSummary
from entities.role import Permission


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(min_length=8)


class TokenData(BaseModel):
    # Always populated: verify_access_token raises when the token carries no id,
    # and verify_refresh_token returns a plain str.
    user_id: str


class UserSchema(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    roles: list[RoleSummary]


class MeSchema(UserSchema):
    permissions: list[Permission]

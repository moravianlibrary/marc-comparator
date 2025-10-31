from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from adapters.dependencies import DatabaseSessionDep

from . import service
from .models import RegisterUserRequest, Token, UserSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])

OAuthFormData = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    db: DatabaseSessionDep, register_user_request: RegisterUserRequest
):
    service.register_user(db, register_user_request)


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuthFormData, db: DatabaseSessionDep
):
    return service.login_for_access_token(form_data, db)


@router.get("/me", response_model=UserSchema)
async def get_current_user(
    current_user: service.CurrentUser, db: DatabaseSessionDep
):
    return service.get_current_user_data(current_user, db)

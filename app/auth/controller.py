from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from adapters.dependencies import DatabaseSessionDep

from . import models, service

router = APIRouter(prefix="/auth", tags=["auth"])

OAuthFormData = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def register_user(
    db: DatabaseSessionDep, register_user_request: models.RegisterUserRequest
):
    service.register_user(db, register_user_request)


@router.post("/token", response_model=models.Token)
async def login_for_access_token(
    form_data: OAuthFormData, db: DatabaseSessionDep
):
    return service.login_for_access_token(form_data, db)

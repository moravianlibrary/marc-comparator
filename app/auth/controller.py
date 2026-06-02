from datetime import timedelta

from fastapi import APIRouter, Cookie, Response
from starlette import status

from adapters.dependencies import DatabaseSessionDep
from config import config

from . import service
from .models import LoginRequest, MeSchema, RegisterUserRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=config.auth.cookie_secure,
        samesite="lax",
        path="/",
        max_age=config.auth.access_token_expire_minutes * 60,
        domain=config.auth.cookie_domain,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=config.auth.cookie_secure,
        samesite="lax",
        path="/api/auth",
        max_age=config.auth.refresh_token_expire_days * 86400,
        domain=config.auth.cookie_domain,
    )


def _clear_auth_cookies(response: Response):
    response.delete_cookie(
        "access_token", path="/", domain=config.auth.cookie_domain, samesite="lax"
    )
    response.delete_cookie(
        "refresh_token", path="/api/auth", domain=config.auth.cookie_domain, samesite="lax"
    )


@router.post("/sign-up", status_code=status.HTTP_201_CREATED)
async def register_user(db: DatabaseSessionDep, register_user_request: RegisterUserRequest):
    service.register_user(db, register_user_request)


@router.post("/login")
async def login(data: LoginRequest, response: Response, db: DatabaseSessionDep):
    user = service.authenticate_user(data.email, data.password, db)
    if not user:
        raise service.AuthenticationError()

    access_token = service.create_access_token(
        user.email,
        user.id,
        timedelta(minutes=config.auth.access_token_expire_minutes),
    )
    refresh_token = service.create_refresh_token(
        user.id,
        timedelta(days=config.auth.refresh_token_expire_days),
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return {"status": "ok"}


@router.post("/refresh")
async def refresh(
    response: Response,
    db: DatabaseSessionDep,
    refresh_token: str = Cookie(default=""),
):
    if not refresh_token:
        raise service.AuthenticationError("No refresh token")

    user_id = service.verify_refresh_token(refresh_token)
    user = service.get_current_user_data(service.TokenData(user_id=user_id), db)

    new_access = service.create_access_token(
        user.email,
        user.id,
        timedelta(minutes=config.auth.access_token_expire_minutes),
    )
    new_refresh = service.create_refresh_token(
        user.id,
        timedelta(days=config.auth.refresh_token_expire_days),
    )
    _set_auth_cookies(response, new_access, new_refresh)
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response):
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=MeSchema)
async def get_current_user(current_user: service.CurrentUser, db: DatabaseSessionDep):
    return service.get_current_user_data(current_user, db)

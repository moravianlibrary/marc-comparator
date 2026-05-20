import logging
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from adapters.database import DatabaseSession, get_db_session
from config import config
from entities.user import User

from . import service
from .controller import _set_auth_cookies

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oidc", tags=["Authentication - OIDC"])


@router.get("/login")
async def oidc_login(redirect: str = "/"):
    """Redirect the user to Keycloak's authorization endpoint."""
    if not config.oidc.enabled:
        return Response(status_code=404)

    params = {
        "client_id": config.oidc.client_id,
        "redirect_uri": config.oidc.redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": redirect,
    }
    url = f"{config.oidc.authorization_endpoint}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/callback")
async def oidc_callback(code: str, state: str = "/"):
    """Handle the Keycloak callback: exchange code for token, provision user, set cookies."""
    if not config.oidc.enabled:
        return Response(status_code=404)

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            config.oidc.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.oidc.redirect_uri,
                "client_id": config.oidc.client_id,
                "client_secret": config.oidc.client_secret,
            },
        )

    if token_response.status_code != 200:
        logger.error(f"OIDC token exchange failed: {token_response.text}")
        return RedirectResponse(url="/login?error=oidc_failed")

    token_data = token_response.json()
    access_token_kc = token_data.get("access_token")

    # Fetch user info from Keycloak
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            config.oidc.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token_kc}"},
        )

    if userinfo_response.status_code != 200:
        logger.error(f"OIDC userinfo failed: {userinfo_response.text}")
        return RedirectResponse(url="/login?error=oidc_failed")

    userinfo = userinfo_response.json()
    email = userinfo.get("email")
    first_name = userinfo.get("given_name", "")
    last_name = userinfo.get("family_name", "")

    if not email:
        logger.error("OIDC userinfo missing email")
        return RedirectResponse(url="/login?error=oidc_no_email")

    # Provision user in app's database (find by email or create)
    db_session: DatabaseSession = get_db_session()
    try:
        user = User.find_by_email(db_session, email)
        if not user:
            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash="",  # No password for OIDC users
            )
            user.save(db_session)
            db_session.commit()
            logger.info(f"OIDC: provisioned new user {email}")
    finally:
        db_session.close()

    # Issue app's own JWT cookies (same as local login)
    app_access_token = service.create_access_token(
        email,
        user.id,
        timedelta(minutes=config.auth.access_token_expire_minutes),
    )
    app_refresh_token = service.create_refresh_token(
        user.id,
        timedelta(days=config.auth.refresh_token_expire_days),
    )

    response = RedirectResponse(url=state, status_code=302)
    _set_auth_cookies(response, app_access_token, app_refresh_token)
    return response


@router.get("/enabled")
async def oidc_enabled():
    """Returns OIDC status. Frontend uses this to show/hide and promote the Keycloak button."""
    return {"enabled": config.oidc.enabled, "default": config.oidc.default}

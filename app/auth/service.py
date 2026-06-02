import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, Request
from jwt import PyJWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from auth.exceptions import AuthenticationError, RegistrationError
from config import config
from entities.role import Role
from entities.user import User

from .models import RegisterUserRequest, TokenData

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return bcrypt_context.hash(password)


def authenticate_user(email: str, password: str, db: Session) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        logging.warning(f"Failed authentication attempt for email: {email}")
        return None
    return user


def create_access_token(email: str, user_id: UUID, expires_delta: timedelta) -> str:
    encode = {
        "sub": email,
        "id": str(user_id),
        "type": "access",
        "exp": datetime.now(UTC) + expires_delta,
    }
    return jwt.encode(encode, config.auth.secret_key, algorithm=config.auth.algorithm)


def create_refresh_token(user_id: UUID, expires_delta: timedelta) -> str:
    encode = {
        "id": str(user_id),
        "type": "refresh",
        "exp": datetime.now(UTC) + expires_delta,
    }
    return jwt.encode(encode, config.auth.secret_key, algorithm=config.auth.algorithm)


def verify_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, config.auth.secret_key, algorithms=[config.auth.algorithm])
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")
        user_id = payload.get("id")
        if not user_id:
            raise AuthenticationError("Missing user ID in token")
        return TokenData(user_id=user_id)
    except PyJWTError as e:
        logging.warning(f"Token verification failed: {str(e)}")
        raise AuthenticationError("Invalid token")


def verify_refresh_token(token: str) -> str:
    """Returns user_id from refresh token."""
    try:
        payload = jwt.decode(token, config.auth.secret_key, algorithms=[config.auth.algorithm])
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        user_id = payload.get("id")
        if not user_id:
            raise AuthenticationError("Missing user ID in token")
        return user_id
    except PyJWTError:
        raise AuthenticationError("Invalid refresh token")


def get_current_user(request: Request) -> TokenData:
    token = request.cookies.get("access_token")
    if not token:
        raise AuthenticationError("Not authenticated")
    return verify_access_token(token)


CurrentUser = Annotated[TokenData, Depends(get_current_user)]


def register_user(db: Session, register_user_request: RegisterUserRequest) -> None:
    try:
        create_user_model = User(
            id=uuid4(),
            email=register_user_request.email,
            first_name=register_user_request.first_name,
            last_name=register_user_request.last_name,
            password_hash=get_password_hash(register_user_request.password),
        )
        db.add(create_user_model)
        db.commit()
        create_user_model.roles.append(Role.get_by_name(db, "Guest"))
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to register user: {register_user_request.email}. Error: {str(e)}")
        raise RegistrationError()


def get_current_user_data(current_user: TokenData, db: Session) -> User:
    user = db.query(User).filter(User.id == UUID(current_user.user_id)).one_or_none()
    if not user:
        raise AuthenticationError("User not found")
    return user

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import PyJWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from auth.exceptions import AuthenticationError
from config import config
from entities.role import Role
from entities.user import User

from . import models

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return bcrypt_context.hash(password)


def authenticate_user(email: str, password: str, db: Session) -> User | bool:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        logging.warning(f"Failed authentication attempt for email: {email}")
        return False
    return user


def create_access_token(
    email: str, user_id: UUID, expires_delta: timedelta
) -> str:
    encode = {
        "sub": email,
        "id": str(user_id),
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(
        encode, config.auth.secret_key, algorithm=config.auth.algorithm
    )


def verify_token(token: str) -> models.TokenData:
    try:
        payload = jwt.decode(
            token, config.auth.secret_key, algorithms=[config.auth.algorithm]
        )
        user_id: str = payload.get("id")
        return models.TokenData(user_id=user_id)
    except PyJWTError as e:
        logging.warning(f"Token verification failed: {str(e)}")
        raise AuthenticationError()


def register_user(
    db: Session, register_user_request: models.RegisterUserRequest
) -> None:
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
        create_user_model.roles.append(Role.get_role_by_name(db, "Guest"))
        db.commit()
    except Exception as e:
        logging.error(
            f"Failed to register user: {register_user_request.email}. "
            f"Error: {str(e)}"
        )
        raise


def get_current_user(
    token: Annotated[str, Depends(oauth2_bearer)],
) -> models.TokenData:
    return verify_token(token)


CurrentUser = Annotated[models.TokenData, Depends(get_current_user)]


def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session
) -> models.Token:
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise AuthenticationError()
    token = create_access_token(
        user.email,
        user.id,
        timedelta(minutes=config.auth.access_token_expire_minutes),
    )
    return models.Token(access_token=token, token_type="bearer")


def get_current_user_data(current_user: models.TokenData, db: Session) -> User:
    user = db.query(User).filter(User.id == UUID(current_user.user_id)).first()
    if not user:
        raise AuthenticationError()

    return user

from typing import Annotated

from fastapi import APIRouter, Body, Query

from adapters.dependencies import DatabaseSessionDep
from common.models import Page, PageRequestParams
from entities.settings import SettingsSchema

from . import service
from .models import RoleSchema, UsersRequestParams

router = APIRouter(prefix="/access-control", tags=["Access Control"])

roles_router = APIRouter(prefix="/roles", tags=["Roles"])
users_router = APIRouter(prefix="/users", tags=["Users"])

router.include_router(roles_router)
router.include_router(users_router)


@roles_router.get("", response_model=Page[RoleSchema])
async def get_roles(
    params: Annotated[PageRequestParams, Query(...)],
    db_session: DatabaseSessionDep,
):
    return service.get_roles(params, db_session)


@roles_router.post("", response_model=RoleSchema)
async def create_role(
    role: Annotated[RoleSchema, Body(...)], db_session: DatabaseSessionDep
):
    return service.create_role(role, db_session)


@roles_router.put("/{role_id}", response_model=RoleSchema)
async def update_role(
    role_id: int,
    role: Annotated[RoleSchema, Body(...)],
    db_session: DatabaseSessionDep,
):
    return service.update_role(role_id, role, db_session)


@roles_router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db_session: DatabaseSessionDep,
):
    return service.delete_role(role_id, db_session)


@users_router.get("", response_model=Page[SettingsSchema])
async def get_users(
    params: Annotated[UsersRequestParams, Query(...)],
    db_session: DatabaseSessionDep,
):
    return service.get_users(params, db_session)


@users_router.patch("/{user_id}/assign-role/{role_id}")
async def assign_role_to_user(
    user_id: str,
    role_id: int,
    db_session: DatabaseSessionDep,
):
    return service.assign_role_to_user(user_id, role_id, db_session)

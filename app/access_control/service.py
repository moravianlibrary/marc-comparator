from fastapi import HTTPException, status

from adapters.database import DatabaseSession
from auth.models import UserSchema
from common.models import Page, PageRequestParams
from entities.role import Role
from entities.user import User

from .models import RoleSchema, UsersRequestParams


def get_roles(
    params: PageRequestParams, db_session: DatabaseSession
) -> Page[RoleSchema]:
    return Page[RoleSchema](
        items=[
            RoleSchema.model_validate(role)
            for role in db_session.query(Role)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
            .all()
        ],
        num_found=len(db_session.query(Role).count()),
    )


def create_role(role: RoleSchema, db_session: DatabaseSession) -> Role:
    db_role = Role(
        name=role.name,
        permissions=role.permissions,
    )
    return db_role.save(db_session)


def update_role(
    role_id: int, role: RoleSchema, db_session: DatabaseSession
) -> Role:
    db_role = Role.get(db_session, role_id)

    if role.immutable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an immutable role",
        )

    db_role.name = role.name
    db_role.permissions = role.permissions

    return db_role.save(db_session)


def delete_role(role_id: int, db_session: DatabaseSession) -> Role:
    db_role = Role.get(db_session, role_id)

    if db_role.immutable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an immutable role",
        )

    if db_role.protected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a protected role",
        )

    return db_role.delete(db_session)


def get_users(
    params: UsersRequestParams, db_session: DatabaseSession
) -> Page[UserSchema]:
    query_base = db_session.query(UserSchema)
    if params.email:
        query_base = query_base.filter(
            UserSchema.email.ilike(f"{params.email}%")
        )

    return Page[UserSchema](
        items=query_base.offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
        .all(),
        num_found=query_base.count(),
    )


def assign_role_to_user(
    user_id: str, role_id: int, db_session: DatabaseSession
) -> User:
    user = User.get(db_session, user_id)
    role = Role.get(db_session, role_id)

    user.roles.append(role)

    return user.save(db_session)

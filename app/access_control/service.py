from adapters.database import DatabaseSession
from auth.models import UserSchema
from common.models import Page, PageRequestParams
from entities.role import Role
from entities.user import User

from .exceptions import (
    ImmutableRoleDeletionException,
    ImmutableRoleModificationException,
    ProtectedRoleDeletionException,
    ProtectedRoleRenameException,
)
from .models import RoleSchema, UsersRequestParams


def get_roles(
    params: PageRequestParams, db_session: DatabaseSession
) -> Page[RoleSchema]:
    return Page[RoleSchema](
        items=[
            RoleSchema.model_validate(role, from_attributes=True)
            for role in db_session.query(Role)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
            .all()
        ],
        num_found=db_session.query(Role).count(),
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

    if db_role.immutable:
        raise ImmutableRoleModificationException()
    if db_role.protected and db_role.name != role.name:
        raise ProtectedRoleRenameException()

    db_role.name = role.name
    db_role.permissions = role.permissions

    return db_role.save(db_session)


def delete_role(role_id: int, db_session: DatabaseSession) -> Role:
    db_role = Role.get(db_session, role_id)

    if db_role.immutable:
        raise ImmutableRoleDeletionException()

    if db_role.protected:
        raise ProtectedRoleDeletionException()

    return db_role.delete(db_session)


def get_users(
    params: UsersRequestParams, db_session: DatabaseSession
) -> Page[UserSchema]:
    query_base = db_session.query(User)
    if params.email:
        query_base = query_base.filter(User.email.ilike(f"{params.email}%"))

    return Page[UserSchema](
        items=[
            UserSchema.model_validate(u, from_attributes=True).model_dump(
                mode="json"
            )
            for u in query_base.offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
            .all()
        ],
        num_found=query_base.count(),
    )


def assign_role_to_user(
    user_id: str, role_id: int, db_session: DatabaseSession
) -> User:
    user = User.get(db_session, user_id)
    role = Role.get(db_session, role_id)

    user.roles.append(role)

    return user.save(db_session)


def unassign_role_from_user(
    user_id: str, role_id: int, db_session: DatabaseSession
) -> User:
    user = User.get(db_session, user_id)
    role = Role.get(db_session, role_id)

    if role in user.roles:
        user.roles.remove(role)

    return user.save(db_session)

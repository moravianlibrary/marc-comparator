from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base, DatabaseSession

from ._operations import BaseOperationsMixin, RetrievalOperationsMixin

if TYPE_CHECKING:
    from .user import User


class Permission(StrEnum):
    ReadRecords = "ReadRecords"
    AddRecords = "AddRecords"
    SyncRecordsFromCatalog = "SyncRecordsFromCatalog"
    ReviewRecords = "ReviewRecords"
    ManageReviews = "ManageReviews"
    ProcessRecords = "ProcessRecords"
    RunPartialRecordTasks = "RunPartialRecordTasks"
    ManageTasks = "ManageTasks"
    ManageAllTasks = "ManageAllTasks"
    ManageAccessControl = "ManageAccessControl"
    ManageAppSettings = "ManageAppSettings"
    ManageTaskSettings = "ManageTaskSettings"


PERMISSION_DEPENDENCIES: dict[Permission, list[Permission]] = {
    Permission.ReadRecords: [],
    Permission.AddRecords: [Permission.ReadRecords],
    Permission.SyncRecordsFromCatalog: [
        Permission.ReadRecords,
        Permission.AddRecords,
        Permission.ManageTasks,
    ],
    Permission.ReviewRecords: [Permission.ReadRecords],
    Permission.ManageReviews: [Permission.ReviewRecords],
    Permission.ProcessRecords: [Permission.ReadRecords],
    Permission.RunPartialRecordTasks: [Permission.ReadRecords],
    Permission.ManageTasks: [Permission.ProcessRecords, Permission.RunPartialRecordTasks],
    Permission.ManageAllTasks: [Permission.ManageTasks],
    Permission.ManageTaskSettings: [Permission.ManageTasks],
    Permission.ManageAccessControl: [],
    Permission.ManageAppSettings: [],
}


def resolve_permissions(permissions: list[Permission]) -> list[Permission]:
    """Expand a permission list to include all transitive dependencies."""
    resolved: set[Permission] = set()
    for perm in permissions:
        resolved.add(perm)
        for dep in PERMISSION_DEPENDENCIES.get(perm, []):
            if dep not in resolved:
                resolved.update(resolve_permissions([dep]))
    return sorted(resolved, key=lambda p: list(Permission).index(p))


class Role(Base, BaseOperationsMixin, RetrievalOperationsMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    _permissions = Column("permissions", JSONB, nullable=False)

    immutable = Column(Boolean, default=False, nullable=False)
    protected = Column(Boolean, default=False, nullable=False)

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="select",
    )

    @property
    def permissions(self) -> list[Permission]:
        return [Permission(p) for p in self._permissions]

    @permissions.setter
    def permissions(self, value: list[Permission]):
        self._permissions = [p.value for p in value]

    @classmethod
    def get_by_name(cls, db_session: DatabaseSession, name: str) -> "Role":
        role = db_session.query(cls).filter(cls.name == name).one_or_none()
        if role is None:
            raise ValueError(f"Role with name '{name}' not found.")
        return role

    @classmethod
    def create_default_roles(cls, db_session: DatabaseSession):
        default_roles = [
            {
                "name": "Admin",
                "permissions": [p for p in Permission],
                "immutable": True,
                "protected": True,
            },
            {
                "name": "Guest",
                "permissions": [Permission.ReadRecords],
                "protected": True,
            },
        ]

        for role_data in default_roles:
            if db_session.query(cls).filter(cls.name == role_data["name"]).count() > 0:
                continue

            role = cls(
                name=role_data["name"],
                permissions=role_data["permissions"],
                immutable=role_data.get("immutable", False),
                protected=role_data.get("protected", False),
            )
            db_session.add(role)

        db_session.commit()

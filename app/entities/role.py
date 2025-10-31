from enum import StrEnum
from typing import TYPE_CHECKING, List

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
    RunRecordTasks = "RunRecordTasks"
    ManageTasks = "ManageTasks"
    ManageAccessControl = "ManageAccessControl"
    ManageAppSettings = "ManageAppSettings"
    ManageTaskSettings = "ManageTaskSettings"


class Role(Base, BaseOperationsMixin, RetrievalOperationsMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    _permissions = Column("permissions", JSONB, nullable=False)

    immutable = Column(Boolean, default=False, nullable=False)
    protected = Column(Boolean, default=False, nullable=False)

    users: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="select",
    )

    @property
    def permissions(self) -> List[Permission]:
        return [Permission(p) for p in self._permissions]

    @permissions.setter
    def permissions(self, value: List[Permission]):
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
            existing_role = (
                db_session.query(cls)
                .filter(cls.name == role_data["name"])
                .one_or_none()
            )
            if existing_role is None:
                role = cls(
                    name=role_data["name"],
                    permissions=role_data["permissions"],
                    immutable=role_data["immutable"],
                    protected=role_data["protected"],
                )
                db_session.add(role)

        db_session.commit()

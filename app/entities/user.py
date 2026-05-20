from typing import List
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from adapters.database import Base

from ._operations import BaseOperationsMixin, RetrievalOperationsMixin
from .role import Permission, Role


class User(Base, BaseOperationsMixin, RetrievalOperationsMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)

    roles: Mapped[List[Role]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="select",
    )

    @property
    def permissions(self) -> List[Permission]:
        perms = set()
        for role in self.roles:
            perms.update([p.value for p in role.permissions])
        return list(perms)

    @classmethod
    def find_by_email(cls, db_session, email: str) -> "User | None":
        return db_session.query(cls).filter_by(email=email).one_or_none()

    def __repr__(self):
        return (
            f"<User(email='{self.email}', "
            f"first_name='{self.first_name}', "
            f"last_name='{self.last_name}')>"
        )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

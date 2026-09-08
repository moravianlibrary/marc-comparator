from uuid import UUID as StdUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.database import Base

from ._operations import BaseOperationsMixin, RetrievalOperationsMixin
from .role import Permission, Role

#: Fixed identity that owns scheduler-created tasks (periodic cleanup,
#: compaction, sync). Seeded on startup; never logs in.
SYSTEM_USER_ID = StdUUID("00000000-0000-0000-0000-000000000001")
SYSTEM_USER_EMAIL = "system@marc-comparator.local"


class User(Base, BaseOperationsMixin, RetrievalOperationsMixin):
    __tablename__ = "users"

    id: Mapped[StdUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String, unique=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    oidc_sub: Mapped[str | None] = mapped_column(String, unique=True)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="select",
    )

    @property
    def permissions(self) -> list[Permission]:
        perms = set()
        for role in self.roles:
            perms.update([p.value for p in role.permissions])
        return list(perms)

    @classmethod
    def find_by_email(cls, db_session, email: str) -> "User | None":
        return db_session.query(cls).filter_by(email=email).one_or_none()

    @classmethod
    def find_by_oidc_sub(cls, db_session, oidc_sub: str) -> "User | None":
        return db_session.query(cls).filter_by(oidc_sub=oidc_sub).one_or_none()

    def __repr__(self):
        return (
            f"<User(email='{self.email}', "
            f"first_name='{self.first_name}', "
            f"last_name='{self.last_name}')>"
        )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[StdUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), primary_key=True)

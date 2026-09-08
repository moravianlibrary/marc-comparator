from datetime import datetime
from enum import StrEnum
from typing import Literal, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import TIMESTAMP, Enum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from adapters.database import Base, DatabaseSession
from entities._operations import BaseOperationsMixin


class SettingsScope(StrEnum):
    Catalog = "catalog"
    Tasks = "tasks"
    Validation = "validators"
    AuthorityLinking = "authority-linkers"
    Comparison = "comparators"
    ProcessRecords = "process-records"
    Maintenance = "maintenance"
    PeriodicSync = "periodic-sync"


type SystemSettingsScope = Literal[
    SettingsScope.Catalog,
    SettingsScope.Tasks,
    SettingsScope.Maintenance,
    SettingsScope.PeriodicSync,
]
type RecordToolsSettingsScope = Literal[
    SettingsScope.Validation,
    SettingsScope.AuthorityLinking,
    SettingsScope.Comparison,
]


class SettingsSchema(BaseModel):
    pass


#: Lets `get`/`save` hand back the concrete schema the caller asked for
#: instead of the `SettingsSchema` base.
SettingsSchemaT = TypeVar("SettingsSchemaT", bound=SettingsSchema)


class Settings(Base, BaseOperationsMixin):
    """Stores configuration settings for specific system features."""

    __tablename__ = "settings"

    # Native PG enum — reads come back as SettingsScope members.
    scope: Mapped[SettingsScope] = mapped_column(Enum(SettingsScope), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    @classmethod
    def get(
        cls,
        db_session: DatabaseSession,
        scope: SettingsScope,
        model: type[SettingsSchemaT],
    ) -> SettingsSchemaT | None:
        """
        Retrieve and validate the settings for the given scope.

        If the stored JSON data cannot be validated against the target model,
        the invalid record will be deleted and `None` returned.

        Parameters
        ----------
        db_session : DatabaseSession
            The database session to use for the operation.
        scope : SettingsScope
            The scope of the settings to retrieve.
        model : Type[SettingsSchema]
            The Pydantic model class to validate the settings data against.

        Returns
        -------
        SettingsSchema | None
            The validated settings data, or `None` if not found or invalid.
        """
        settings = db_session.get(cls, scope)
        if settings is None:
            return None

        try:
            return model.model_validate(settings.data)
        except ValidationError:
            db_session.delete(settings)
            db_session.commit()
            return None

    @classmethod
    def upsert(
        cls,
        db_session: DatabaseSession,
        scope: SettingsScope,
        data: BaseModel,
        model: type[SettingsSchemaT],
    ) -> SettingsSchemaT:
        """
        Insert or update settings for the given scope.

        Parameters
        ----------
        db_session : DatabaseSession
            The database session to use for the operation.
        scope : SettingsScope
            The scope of the settings to save.
        data : BaseModel
            The settings data to save.

        Returns
        -------
        Settings
            The saved settings instance.
        """
        settings = db_session.get(cls, scope)

        data_jsonb = data.model_dump(mode="json", by_alias=True)
        if settings:
            settings.data = data_jsonb
        else:
            settings = cls(scope=scope, data=data_jsonb)

        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)

        return model.model_validate(settings.data)

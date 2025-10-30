from enum import StrEnum
from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import TIMESTAMP, Column, Enum, func
from sqlalchemy.dialects.postgresql import JSONB

from adapters.database import Base, DatabaseSession
from entities._operations import BaseOperationsMixin


class SettingsScope(StrEnum):
    Validation = "Validation"
    AuthorityLinking = "AuthorityLinking"
    Comparison = "Comparison"


SettingsModel = TypeVar("T", bound=BaseModel)
SettingsSchema = Dict[str, Any]


class Settings(Base, BaseOperationsMixin):
    """Stores configuration settings for specific system features."""

    __tablename__ = "settings"

    scope = Column(Enum(SettingsScope), primary_key=True)
    data = Column(JSONB, nullable=False)

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @classmethod
    def get(
        cls,
        db_session: DatabaseSession,
        scope: SettingsScope,
        model: Type[SettingsModel],
    ) -> SettingsModel | None:
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
        model : Type[SettingsModel]
            The Pydantic model class to validate the settings data against.

        Returns
        -------
        SettingsModel | None
            The validated settings data, or `None` if not found or invalid.
        """
        try:
            settings = db_session.get(cls, scope)

            return model.model_validate(settings.data) if settings else None
        except ValidationError:
            db_session.delete(settings)
            db_session.commit()
            return None

    @classmethod
    def save(
        cls,
        db_session: DatabaseSession,
        scope: SettingsScope,
        data: BaseModel,
        model: Type[SettingsModel],
    ) -> SettingsModel:
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

        data_jsonb = data.model_dump(mode="json")
        if settings:
            settings.data = data_jsonb
        else:
            settings = cls(scope=scope, data=data_jsonb)

        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)

        return model.model_validate(settings.data)

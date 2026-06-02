from typing import Any

from adapters.database import DatabaseSession
from entities.settings import Settings, SettingsSchema, SettingsScope
from settings.exceptions import (
    SettingsNotFoundError,
    SettingsPartNotFoundError,
)

from .models import SETTINGS_MODEL_DISPATCHER


def get_settings(scope: SettingsScope, db_session: DatabaseSession) -> SettingsSchema:
    settings_cls = SETTINGS_MODEL_DISPATCHER.get(scope)

    settings = Settings.get(db_session, scope, settings_cls)

    if settings is None:
        raise SettingsNotFoundError(scope)

    return settings


def set_settings(
    scope: SettingsScope, settings: SettingsSchema, db_session: DatabaseSession
) -> SettingsSchema:
    settings_cls = SETTINGS_MODEL_DISPATCHER.get(scope)

    settings_validated = settings.model_validate(settings)

    return Settings.save(db_session, scope, settings_validated, settings_cls)


def get_settings_part(
    scope: SettingsScope,
    part_name: str,
    db_session: DatabaseSession,
) -> Any:
    """
    Retrieve a specific part/attribute from settings for a given scope.
    Raises SettingsPartNotFoundError if the part is missing.

    Parameters
    ----------
    scope : SettingsScope
        The scope of the settings (e.g., Comparison, Validation, App).
    part_name : str
        The attribute/key to retrieve from the settings.
    db_session : DatabaseSessionDep
        Database session.

    Returns
    -------
    Any
        The value of the requested part in the settings.
    """
    settings = get_settings(scope, db_session)

    value = getattr(settings, part_name, None)

    if value is None:
        # Try using alias
        for field_name, field in settings.model_fields.items():
            if field.alias == part_name:
                value = getattr(settings, field_name, None)
                break

    if value is None:
        raise SettingsPartNotFoundError(scope, part_name)

    return value

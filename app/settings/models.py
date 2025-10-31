from typing import Dict

from aleph_nought import AlephConfig

from authority_linking.models import AuthorityLinkingSettings
from comparison.models import ComparisonSettings
from entities.settings import SettingsSchema, SettingsScope
from tasks.models import TaskSettings
from validation.models import ValidationSettings


class CatalogSettings(SettingsSchema):
    clients: Dict[str, AlephConfig]


SETTINGS_MODEL_DISPATCHER: Dict[SettingsScope, type[SettingsSchema]] = {
    SettingsScope.Catalog: CatalogSettings,
    SettingsScope.Task: TaskSettings,
    SettingsScope.Validation: ValidationSettings,
    SettingsScope.AuthorityLinking: AuthorityLinkingSettings,
    SettingsScope.Comparison: ComparisonSettings,
}


AppSettingsSchemas = CatalogSettings | TaskSettings
TaskSettingsSchemas = (
    ValidationSettings | AuthorityLinkingSettings | ComparisonSettings
)

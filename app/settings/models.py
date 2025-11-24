from typing import Dict

from authority_linking.models import AuthorityLinkingSettings
from catalog_records.models import CatalogSettings
from comparison.models import ComparisonSettings
from entities.settings import SettingsSchema, SettingsScope
from tasks.models import TaskSettings
from validation.models import ValidationSettings

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

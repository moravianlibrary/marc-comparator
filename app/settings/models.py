from typing import Dict

from authority_linking.models import AuthorityLinkingSettings
from catalog_records.models import CatalogSettings
from catalog_records.models import ProcessRecordsSettings
from comparison.models import ComparisonSettings
from entities.settings import SettingsSchema, SettingsScope
from tasks.models import TaskSettings
from validation.models import ValidationSettings

SETTINGS_MODEL_DISPATCHER: Dict[SettingsScope, type[SettingsSchema]] = {
    SettingsScope.Catalog: CatalogSettings,
    SettingsScope.Tasks: TaskSettings,
    SettingsScope.AuthorityLinking: AuthorityLinkingSettings,
    SettingsScope.Comparison: ComparisonSettings,
    SettingsScope.Validation: ValidationSettings,
    SettingsScope.ProcessRecords: ProcessRecordsSettings,
}


AppSettingsSchemas = CatalogSettings | TaskSettings
TaskSettingsSchemas = (
    ValidationSettings
    | AuthorityLinkingSettings
    | ComparisonSettings
    | ProcessRecordsSettings
)

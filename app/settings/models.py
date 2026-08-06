from authority_linking.models import AuthorityLinkingSettings
from catalog_records.models import CatalogSettings, ProcessRecordsSettings
from comparison.models import ComparisonSettings
from entities.settings import SettingsSchema, SettingsScope
from maintenance.models import MaintenanceSettings
from periodic_sync.models import PeriodicSyncSettings
from tasks.models import TaskSettings
from validation.models import ValidationSettings

SETTINGS_MODEL_DISPATCHER: dict[SettingsScope, type[SettingsSchema]] = {
    SettingsScope.Catalog: CatalogSettings,
    SettingsScope.Tasks: TaskSettings,
    SettingsScope.AuthorityLinking: AuthorityLinkingSettings,
    SettingsScope.Comparison: ComparisonSettings,
    SettingsScope.Validation: ValidationSettings,
    SettingsScope.ProcessRecords: ProcessRecordsSettings,
    SettingsScope.Maintenance: MaintenanceSettings,
    SettingsScope.PeriodicSync: PeriodicSyncSettings,
}


AppSettingsSchemas = CatalogSettings | TaskSettings | MaintenanceSettings | PeriodicSyncSettings
TaskSettingsSchemas = (
    ValidationSettings | AuthorityLinkingSettings | ComparisonSettings | ProcessRecordsSettings
)

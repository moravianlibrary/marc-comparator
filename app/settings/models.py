from typing import Dict

from aleph_nought import AlephConfig
from pydantic import Field

from authority_linking.models import AuthorityLinkingSettings
from comparison.models import ComparisonSettings
from entities.settings import SettingsSchema, SettingsScope
from validation.models import ValidationSettings


class CatalogSettings(SettingsSchema):
    clients: Dict[str, AlephConfig]


class TaskSettings(SettingsSchema):
    progress_update_interval: int = Field(
        100,
        description="Interval (in number of records) to update task progress.",
    )
    indexing_batch_size: int = Field(
        500,
        description="Number of records to index in a single batch operation.",
    )


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

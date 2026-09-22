from datetime import datetime

from pydantic import BaseModel, Field

from entities.settings import SettingsSchema
from entities.task import TaskSchema


class PluginHarvestSchedule(SettingsSchema):
    """Scheduling preference for one discovered harvest plugin."""

    enabled: bool = False
    interval_hours: int = Field(default=24, gt=0)


class PluginHarvestSettings(SettingsSchema):
    """Schedule preferences keyed by stable plugin registry name."""

    plugins: dict[str, PluginHarvestSchedule] = Field(default_factory=dict)


class HarvestRunRequest(BaseModel):
    full_rebuild: bool = False


class HarvestPluginStatus(BaseModel):
    name: str
    scope: str
    enabled: bool
    interval_hours: int
    ready: bool
    schema_version: int
    source_identity: str | None = None
    state_source_identity: str | None = None
    compatible: bool
    watermark: str | None = None
    records: int | None = None
    last_harvest_at: datetime | None = None
    current_task: TaskSchema | None = None

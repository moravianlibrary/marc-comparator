from datetime import datetime

from pydantic import BaseModel, Field

from adapters.cron import DAILY, CronExpression
from entities.settings import SettingsSchema
from entities.task import TaskSchema


class PluginHarvestSchedule(SettingsSchema):
    """Scheduling preference for one discovered harvest plugin."""

    enabled: bool = False
    cron: CronExpression = DAILY


class PluginHarvestSettings(SettingsSchema):
    """Schedule preferences keyed by stable plugin registry name."""

    plugins: dict[str, PluginHarvestSchedule] = Field(default_factory=dict)


class HarvestRunRequest(BaseModel):
    full_rebuild: bool = False


class HarvestPluginStatus(BaseModel):
    name: str
    scope: str
    enabled: bool
    cron: str
    ready: bool
    schema_version: int
    source_identity: str | None = None
    state_source_identity: str | None = None
    compatible: bool
    watermark: str | None = None
    records: int | None = None
    total_records: int | None = None
    last_harvest_at: datetime | None = None
    current_task: TaskSchema | None = None

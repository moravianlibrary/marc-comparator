from pydantic import BaseModel, Field

from catalog_records.models import RecordFilter
from entities.settings import SettingsSchema

from . import UsedComparatorConfig


class ComparisonSettings(SettingsSchema):
    comparator: UsedComparatorConfig | None = Field(UsedComparatorConfig())


class ComparisonTaskData(BaseModel):
    target_base: str
    filters: RecordFilter = RecordFilter()

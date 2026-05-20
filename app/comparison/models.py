from marc_comparator.comparators import Comparator, IntiimComparatorConfig
from pydantic import BaseModel, Field

from catalog_records.models import RecordFilter
from entities.settings import SettingsSchema


class ComparisonSettings(SettingsSchema):
    intiim: IntiimComparatorConfig | None = Field(IntiimComparatorConfig())


class ComparisonTaskData(BaseModel):
    comparator: Comparator
    target_base: str
    filters: RecordFilter = RecordFilter()

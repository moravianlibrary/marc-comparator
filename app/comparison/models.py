from marc_comparator.comparators import Comparator, IntiimComparatorConfig
from pydantic import BaseModel, Field

from adapters.indexer import IndexerQuery
from entities.settings import SettingsSchema


class ComparisonSettings(SettingsSchema):
    intiim: IntiimComparatorConfig | None = Field(IntiimComparatorConfig())


class ComparisonTaskData(BaseModel):
    comparator: Comparator
    target_base: str
    query: IndexerQuery

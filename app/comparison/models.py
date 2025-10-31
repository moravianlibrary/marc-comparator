from marc_comparator_sdk.comparators import (
    Comparator,
    RuleBasedComparatorConfig,
)
from pydantic import BaseModel, Field

from adapters.indexer import IndexerQuery
from entities.settings import SettingsSchema


class ComparisonSettings(SettingsSchema):
    rule_based: RuleBasedComparatorConfig | None = Field(
        None, alias="rule-based"
    )


class ComparisonTaskData(BaseModel):
    comparator: Comparator
    target_base: str
    query: IndexerQuery

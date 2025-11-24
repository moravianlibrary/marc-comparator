from typing import List

from marc_comparator.validators import KrameriusLinksValidatorConfig, Validator
from pydantic import BaseModel, Field

from adapters.indexer import IndexerQuery
from entities.settings import SettingsSchema


class ValidationSettings(SettingsSchema):
    kramerius_links: KrameriusLinksValidatorConfig | None = Field(
        KrameriusLinksValidatorConfig(), alias="kramerius-links"
    )


class ValidationTaskData(BaseModel):
    validators: List[Validator] = Field(..., min_length=1)
    query: IndexerQuery

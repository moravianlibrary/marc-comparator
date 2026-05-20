from typing import List

from marc_comparator.validators import KrameriusLinksValidatorConfig, Validator
from pydantic import BaseModel, Field

from catalog_records.models import RecordFilter
from entities.settings import SettingsSchema


class ValidationSettings(SettingsSchema):
    kramerius_links: KrameriusLinksValidatorConfig | None = Field(
        KrameriusLinksValidatorConfig(), alias="kramerius-links"
    )


class ValidationTaskData(BaseModel):
    validators: List[Validator] = Field(..., min_length=1)
    filters: RecordFilter = RecordFilter()

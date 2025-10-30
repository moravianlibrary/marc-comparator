from adapters.tasks import ManagedTask
from entities.catalog_record import CatalogRecord
from entities.catalog_record_validity import CatalogRecordValidity

from typing import List

from marc_comparator_sdk.validators._base import (
    BaseValidator,
    ValidationResult,
    ValidityStatus
)

from marc_comparator_sdk.validators.kramerius_links import (
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig
)

def _get_validators() -> List[BaseValidator]:
    """
    Return all validators implemented in SDK as list
    """
    validators = []

    kramerius_config = KrameriusLinksValidatorConfig()
    validators.append(KrameriusLinksValidator(kramerius_config))
    
    # TODO: Add other validators after they are implemented in SDK
    return validators


async def _validate_single_record(
    record: CatalogRecord,
    validators: List[BaseValidator],
) -> tuple[bool, List[ValidationResult]]:
    pass


async def validate_records_task(task_id: str) -> None:
    pass

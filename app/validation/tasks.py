import logging
from dataclasses import dataclass
from typing import List

from marc_comparator.validators import (
    VALIDATOR_DISPATCHER,
    BaseValidator,
    Validator,
)

from adapters.database import DatabaseSession
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from catalog_records.search import build_filtered_query
from entities.catalog_record import CatalogRecord
from entities.settings import Settings, SettingsScope
from entities.validation import Validation

from .models import ValidationSettings, ValidationTaskData


@dataclass(slots=True)
class ValidatorInstance:
    type: Validator
    instance: BaseValidator


def load_validators(
    db_session: DatabaseSession,
    validators: List[Validator],
    logger: logging.Logger,
) -> List[ValidatorInstance] | None:
    """Load settings from DB and initialize validators. Returns None on failure."""
    settings = Settings.get(
        db_session, SettingsScope.Validation, ValidationSettings
    )
    if not settings:
        return None
    result = init_validators(settings, validators, logger)
    return result or None


def init_validators(
    settings: ValidationSettings,
    validators: List[Validator],
    logger: logging.Logger,
) -> List[ValidatorInstance]:
    validator_instances: List[ValidatorInstance] = []

    for validator in validators:
        validator_cls = VALIDATOR_DISPATCHER.get(validator)

        if not validator_cls:
            logger.error(f"Unknown validator: {validator}")
            continue

        validator_config = (
            getattr(settings, validator.value.replace("-", "_"), None)
            if validator_cls.config_model
            else None
        )

        validator_instance = (
            validator_cls(validator_config)
            if validator_config
            else validator_cls()
        )

        validator_instances.append(
            ValidatorInstance(type=validator, instance=validator_instance)
        )

    return validator_instances


async def handle_catalog_record_validation(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    validator_instance: ValidatorInstance,
) -> None:
    results = await validator_instance.instance.run(
        catalog_record.get_record(db_session)
    )

    Validation.delete_by_record_and_validator(
        db_session,
        catalog_record.id,
        validator_instance.type.value,
    )

    Validation.save_all(
        db_session,
        catalog_record.id,
        validator_instance.type.value,
        results,
    )


async def validate_records(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = ValidationTaskData.model_validate(ctx.task.data)

        validator_instances = load_validators(
            ctx.db_session, data.validators, ctx.logger
        )
        if not validator_instances:
            ctx.logger.error("Validators could not be initialized")
            return

        record_ids = [
            r.id for r in build_filtered_query(
                ctx.db_session, data.filters
            ).with_entities(CatalogRecord.id).all()
        ]
        ctx.total = len(record_ids) * len(validator_instances)

        for record_id in record_ids:
            catalog_record = ctx.db_session.get(CatalogRecord, record_id)
            for validator_instance in validator_instances:
                try:
                    await handle_catalog_record_validation(
                        ctx.db_session,
                        catalog_record,
                        validator_instance,
                    )

                    handle_batch_progress_snippet(ctx)

                except ValueError as e:
                    ctx.logger.warning(
                        f"Skipping record {catalog_record.id} "
                        f"with validator {validator_instance.type.value}: {e}"
                    )
                    handle_batch_progress_snippet(ctx)

                except Exception as e:
                    ctx.db_session.rollback()
                    ctx.logger.error(
                        f"Failed validating record {catalog_record.id} "
                        f"with validator {validator_instance.type.value}:\n{e}"
                    )
                    handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(
            "Finished validating records, "
            f"total records processed: {ctx.progress}"
        )

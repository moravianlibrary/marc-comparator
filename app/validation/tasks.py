from dataclasses import dataclass
from typing import List

from marc_comparator.validators import (
    VALIDATOR_DISPATCHER,
    BaseValidator,
    Validator,
)
from marcdantic import MarcRecord

from adapters.tasks import ManagedTask
from catalog_records.tasks import (
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from entities.catalog_record import CatalogRecord
from entities.settings import Settings, SettingsScope
from entities.validation import Validation

from .models import ValidationSettings, ValidationTaskData


@dataclass(slots=True)
class ValidatorInstance:
    type: Validator
    instance: BaseValidator


async def validate_records(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = ValidationTaskData.model_validate(ctx.task.data)
        settings = Settings.get(
            ctx.db_session,
            SettingsScope.Validation,
            ValidationSettings,
        )

        if not settings:
            ctx.logger.error("Validation settings not found")
            return

        validator_instances: List[ValidatorInstance] = []

        for validator in data.validators:
            try:
                validator_cls = VALIDATOR_DISPATCHER.get(validator)

                if not validator_cls:
                    ctx.logger.error(f"Unknown validator: {validator}")
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
                    ValidatorInstance(
                        type=validator, instance=validator_instance
                    )
                )
            except Exception as e:
                ctx.logger.error(
                    f"Error initializing validator '{validator}':\n{e}"
                )

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
            for validator_instance in validator_instances:
                try:
                    results = await validator_instance.instance.run(
                        MarcRecord.from_mrc(catalog_record.marc)
                    )

                    Validation.delete_by_record_and_validator(
                        ctx.db_session,
                        catalog_record.id,
                        validator_instance.type.value,
                    )

                    Validation.save_all(
                        ctx.db_session,
                        catalog_record.id,
                        validator_instance.type.value,
                        results,
                    )

                    await handle_batch_progress_snippet(ctx, catalog_record)

                except Exception as e:
                    ctx.logger.error(
                        f"Failed validating record {catalog_record.id} "
                        f"with validator {validator_instance.type.value}:\n{e}"
                    )

        await handle_final_batch_snippet(ctx)

        ctx.logger.info(
            "Finished comparing of records, "
            f"total records processed: {ctx.progress}"
        )

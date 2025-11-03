from dataclasses import dataclass
from typing import List

from marc_comparator.validators import (
    VALIDATOR_DISPATCHER,
    BaseValidator,
    Validator,
)
from marcdantic import MarcRecord

from adapters.tasks import ManagedTask
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
        progress_interval = ctx.task_settings.progress_update_interval
        batch_size = ctx.task_settings.indexing_batch_size

        data = ValidationTaskData.model_validate(ctx.task.data)
        settings = Settings.get(
            ctx.db_session,
            SettingsScope.Validation,
            ValidationSettings,
        )

        if not settings:
            raise ValueError("Validation settings not found")

        validator_instances: List[ValidatorInstance] = []

        for validator in data.validators:
            validator_cls = VALIDATOR_DISPATCHER.get(validator)

            if not validator_cls:
                raise ValueError(f"Unknown validator: {validator}")

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

        progress = 0
        reindex_batch: List[CatalogRecord] = []

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
            for validator_instance in validator_instances:
                result = await validator_instance.instance.run(
                    MarcRecord.from_mrc(catalog_record.marc)
                )

                validation = Validation.find(
                    ctx.db_session,
                    catalog_record_id=catalog_record.id,
                    validator=validator_instance.type.value,
                )

                if validation:
                    validation.result = result.model_dump()
                else:
                    validation = Validation(
                        catalog_record_id=catalog_record.id,
                        validator=validator_instance.type.value,
                        result=result.model_dump(),
                    )

                validation.save(ctx.db_session)

            reindex_batch.append(catalog_record)
            progress += 1

            if progress % progress_interval == 0:
                ctx.logger.info(f"Processed {progress} records so far")

            if progress % batch_size == 0:
                ctx.logger.info(
                    f"Indexing batch of {len(reindex_batch)} records..."
                )

                ctx.db_session.commit()
                await CatalogRecord.bulk_index(reindex_batch)

                reindex_batch = []

        if reindex_batch:
            ctx.logger.info(
                f"Indexing final batch of {len(reindex_batch)} records..."
            )
            ctx.db_session.commit()
            await CatalogRecord.bulk_index(reindex_batch)

        ctx.logger.info(
            "Finished comparing of records, "
            f"total records processed: {progress}"
        )

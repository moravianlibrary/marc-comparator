import logging
from collections.abc import Sequence
from dataclasses import dataclass

from marc_comparator.validators import (
    VALIDATOR_DISPATCHER,
    BaseValidator,
    Validator,
)
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from authority_linking.tasks import (
    LINK_PREFETCH_WINDOW,
    announce_window,
    windows,
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
    validators: list[Validator],
    logger: logging.Logger,
) -> list[ValidatorInstance] | None:
    """Load settings from DB and initialize validators. Returns None on failure."""
    settings = Settings.get(db_session, SettingsScope.Validation, ValidationSettings)
    if not settings:
        return None
    result = init_validators(settings, validators, logger)
    from harvest.storage import bind_plugin_storage

    for validator in result:
        bind_plugin_storage(validator.type.value, validator.instance, db_session, logger)
    return result or None


def init_validators(
    settings: ValidationSettings,
    validators: list[Validator],
    logger: logging.Logger,
) -> list[ValidatorInstance]:
    validator_instances: list[ValidatorInstance] = []

    for validator in validators:
        validator_cls = VALIDATOR_DISPATCHER.get(validator)

        if not validator_cls:
            logger.error(f"Unknown validator: {validator}")
            continue

        config_model = validator_cls.config_model
        if config_model is None:
            validator_instance = validator_cls()
        else:
            # Settings may store null for a configured validator; fall back to the
            # config model's own defaults rather than constructing without one.
            stored = getattr(settings, validator.value.replace("-", "_"), None)
            validator_instance = validator_cls(stored if stored is not None else config_model())

        validator_instances.append(ValidatorInstance(type=validator, instance=validator_instance))

    return validator_instances


async def handle_catalog_record_validation(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
    validator_instance: ValidatorInstance,
    record: MarcRecord | None = None,
) -> None:
    # Callers running every validator over one record already hold it parsed;
    # reading it back per validator was a sector read and a parse each time.
    results = await validator_instance.instance.run(
        record if record is not None else catalog_record.get_record(db_session)
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


async def announce_validation_window(
    db_session: DatabaseSession,
    record_ids: Sequence[str],
    validators: list[ValidatorInstance],
    logger: logging.Logger,
) -> None:
    """Tell every validator which records are coming before walking them."""

    records: list[MarcRecord] = []
    for record_id in record_ids:
        catalog_record = db_session.get(CatalogRecord, record_id)
        if catalog_record is None:
            continue
        try:
            records.append(catalog_record.get_record(db_session))
        except ValueError:
            # Reported by the caller when it reaches this record; a window is
            # a hint, and must not turn one record's problem into the batch's.
            continue

    await announce_window(validators, records, logger, lambda instance: instance.type.value)


async def validate_records(task_id: str) -> None:
    async with ManagedTask(task_id=task_id, lock_key=f"task-run-{task_id}") as ctx:
        data = ValidationTaskData.model_validate(ctx.task.data)

        validator_instances = load_validators(ctx.db_session, data.validators, ctx.logger)
        if not validator_instances:
            ctx.logger.error("Validators could not be initialized")
            return

        record_ids = [
            r.id
            for r in build_filtered_query(ctx.db_session, data.filters)
            .with_entities(CatalogRecord.id)
            .all()
        ]
        ctx.total = len(record_ids) * len(validator_instances)

        for window in windows(record_ids, LINK_PREFETCH_WINDOW):
            await announce_validation_window(
                ctx.db_session, window, validator_instances, ctx.logger
            )

            for record_id in window:
                catalog_record = ctx.db_session.get(CatalogRecord, record_id)
                if catalog_record is None:
                    # Deleted between building the id list and getting here —
                    # the total counts one step per validator, so advance all.
                    for _ in validator_instances:
                        handle_batch_progress_snippet(ctx)
                    continue

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

        ctx.logger.info(f"Finished validating records, total records processed: {ctx.progress}")

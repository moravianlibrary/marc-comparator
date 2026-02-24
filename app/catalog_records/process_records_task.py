from ast import List
from collections import defaultdict

from celery.app.base import Settings
from marc_comparator.authority_linkers import AuthorityLinker
from marc_comparator.comparators import Comparator
from marc_comparator.validators import Validator
from marcdantic import MarcRecord
from pydantic import Field

from adapters.indexer import IndexerQuery
from adapters.tasks import ManagedTask
from authority_linking.models import AuthorityLinkingSettings
from authority_linking.tasks import (
    LinkActionResult,
    find_best_link_for_record,
    handle_catalog_record_link_action,
    init_authority_linkers,
)
from catalog_records.tasks import (
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from comparison.models import ComparisonSettings
from comparison.tasks import handle_catalog_record_comparison, init_comparator
from config import config
from entities.catalog_record import CatalogRecord
from entities.settings import SettingsSchema, SettingsScope
from validation.models import ValidationSettings
from validation.tasks import handle_catalog_record_validation, init_validators


class ProcessRecordsSettings(SettingsSchema):
    target_bases: List[str] = Field(..., min_length=1)
    authority_linkers: List[AuthorityLinker] = Field(..., min_length=1)
    comparator: Comparator
    validators: List[Validator]


async def process_records(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        settings: ProcessRecordsSettings | None = Settings.get(
            ctx.db_session,
            SettingsScope.ProcessRecords,
            ProcessRecordsSettings,
        )

        if not settings:
            ctx.logger.error("Authority linking settings not found")
            return

        query = IndexerQuery.model_validate(ctx.task.data)

        ctx.logger.info("Starting processing of catalog records")

        al_settings = Settings.get(
            ctx.db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings,
        )

        authority_linkers = init_authority_linkers(
            al_settings, settings.authority_linkers
        )

        c_settings = Settings.get(
            ctx.db_session,
            SettingsScope.Comparison,
            ComparisonSettings,
        )

        comparator = init_comparator(c_settings, settings.comparator)

        validation_settings = Settings.get(
            ctx.db_session,
            SettingsScope.Validation,
            ValidationSettings,
        )

        validators = init_validators(validation_settings, settings.validators)

        counters: defaultdict[LinkActionResult, int] = defaultdict(int)

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, query
        ):
            marc_record = MarcRecord.from_mrc(catalog_record.marc)

            # 1. Find the best link for the record
            for target_base in settings.target_bases:
                found_link, linker_instance = await find_best_link_for_record(
                    catalog_record,
                    authority_linkers,
                    target_base,
                    marc_record,
                    ctx.logger,
                )

                results = handle_catalog_record_link_action(
                    ctx.db_session,
                    catalog_record,
                    found_link,
                    linker_instance,
                    target_base,
                )

                for result in results:
                    counters[result] += 1

            # 2. Compare the record with the authority links
            for authority_link in catalog_record.authority_links:
                await handle_catalog_record_comparison(
                    ctx.db_session,
                    catalog_record,
                    authority_link,
                    comparator,
                    ctx.logger,
                )

            # 3. Validate the record
            for validator in validators:
                await handle_catalog_record_validation(
                    ctx.db_session,
                    catalog_record,
                    validator,
                    ctx.logger,
                )

            # 4. Mark the record as processed
            catalog_record.processed_at = config.timestamp

            await handle_batch_progress_snippet(ctx, catalog_record)

        await handle_final_batch_snippet(ctx)

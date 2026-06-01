import logging

from marc_comparator.comparators import BaseComparator

from adapters.database import DatabaseSession
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from catalog_records.search import build_filtered_query
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.settings import Settings, SettingsScope

from . import UsedComparator, UsedComparatorClass
from .models import ComparisonSettings, ComparisonTaskData


def load_comparator(db_session: DatabaseSession) -> BaseComparator | None:
    """Load settings from DB and initialize comparator. Returns None on failure."""
    settings = Settings.get(
        db_session, SettingsScope.Comparison, ComparisonSettings
    )
    if not settings:
        return None
    try:
        return init_comparator(settings)
    except ValueError:
        return None


def init_comparator(settings: ComparisonSettings) -> BaseComparator:
    config = settings.comparator
    if config is not None:
        return UsedComparatorClass(config)
    return UsedComparatorClass()


async def handle_catalog_record_comparison(
    db_session: DatabaseSession,
    comparator: BaseComparator,
    logger: logging.Logger,
    target_base: str,
    catalog_record: CatalogRecord,
) -> None:
    link = next(
        (
            al
            for al in catalog_record.authority_links
            if al.base == target_base
        ),
        None,
    )

    if link is None:
        logger.info(
            f"No authority link found for {catalog_record.id} "
            f"to target base {target_base}"
        )
        return

    result = await comparator.run(
        catalog_record.get_record(db_session),
        link.authority_record.get_record(db_session),
    )

    comparison = Comparison.find(
        db_session,
        catalog_record.id,
        UsedComparator.value,
        target_base,
    )

    if comparison:
        comparison.other_record_id = link.authority_record.id
        comparison.result = result.model_dump()
    else:
        comparison = Comparison(
            main_record_id=catalog_record.id,
            comparator=UsedComparator.value,
            base=target_base,
            other_record_id=link.authority_record.id,
            result=result.model_dump(),
        )

    comparison.save(db_session)


async def compare_records(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = ComparisonTaskData.model_validate(ctx.task.data)

        comparator = load_comparator(ctx.db_session)
        if not comparator:
            ctx.logger.error("Comparator could not be initialized")
            return

        record_ids = [
            r.id for r in build_filtered_query(
                ctx.db_session, data.filters
            ).with_entities(CatalogRecord.id).all()
        ]
        ctx.total = len(record_ids)

        for record_id in record_ids:
            catalog_record = ctx.db_session.get(CatalogRecord, record_id)
            try:
                await handle_catalog_record_comparison(
                    ctx.db_session,
                    comparator,
                    ctx.logger,
                    data.target_base,
                    catalog_record,
                )

                handle_batch_progress_snippet(ctx)

            except ValueError as e:
                ctx.logger.warning(
                    f"Skipping record {catalog_record.id}: {e}"
                )
                handle_batch_progress_snippet(ctx)

            except Exception as e:
                ctx.db_session.rollback()
                ctx.logger.error(
                    f"Failed comparing record {catalog_record.id}:\n{e}"
                )
                handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(
            "Finished comparing of records, "
            f"total records processed: {ctx.progress}"
        )

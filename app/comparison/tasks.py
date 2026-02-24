import logging

from marc_comparator.comparators import (
    COMPARATOR_DISPATCHER,
    BaseComparator,
    Comparator,
)
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.settings import Settings, SettingsScope

from .models import ComparisonSettings, ComparisonTaskData


def init_comparator(
    settings: ComparisonSettings, comparator: Comparator
) -> BaseComparator:
    comparator_cls = COMPARATOR_DISPATCHER.get(comparator)
    if not comparator_cls:
        raise ValueError(f"Unknown comparator: {comparator}")

    comparator_config = (
        getattr(settings, comparator.value.replace("-", "_"), None)
        if comparator_cls.config_model
        else None
    )

    return (
        comparator_cls(comparator_config)
        if comparator_config
        else comparator_cls()
    )


async def handle_catalog_record_comparison(
    db_session: DatabaseSession,
    comparator_name: str,
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
        MarcRecord.from_mrc(catalog_record.marc),
        MarcRecord.from_mrc(link.authority_record.marc),
    )

    comparison = Comparison.find(
        db_session,
        catalog_record.id,
        comparator_name,
        link.authority_record.id,
    )

    if comparison:
        comparison.result = result.model_dump()
    else:
        comparison = Comparison(
            main_record_id=catalog_record.id,
            comparator=comparator_name,
            other_record_id=link.authority_record.id,
            result=result.model_dump(),
        )

    comparison.save(db_session)


async def compare_records(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        data = ComparisonTaskData.model_validate(ctx.task.data)
        settings = Settings.get(
            ctx.db_session,
            SettingsScope.Comparison,
            ComparisonSettings,
        )

        if not settings:
            ctx.logger.error("Comparison settings not found")
            return

        try:
            comparator = init_comparator(settings, data.comparator)
        except ValueError as e:
            ctx.logger.error(str(e))
            return

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
            try:
                await handle_catalog_record_comparison(
                    ctx.db_session,
                    data.comparator.value,
                    comparator,
                    ctx.logger,
                    data.target_base,
                    catalog_record,
                )

                await handle_batch_progress_snippet(ctx, catalog_record)

            except Exception as e:
                ctx.logger.error(
                    f"Failed comparing record {catalog_record.id}:\n{e}"
                )

        await handle_final_batch_snippet(ctx)

        ctx.logger.info(
            "Finished comparing of records, "
            f"total records processed: {ctx.progress}"
        )

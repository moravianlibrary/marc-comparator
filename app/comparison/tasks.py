from marc_comparator.comparators import COMPARATOR_DISPATCHER
from marcdantic import MarcRecord

from adapters.tasks import ManagedTask
from catalog_records.tasks import (
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.settings import Settings, SettingsScope

from .models import ComparisonSettings, ComparisonTaskData


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

        comparator_cls = COMPARATOR_DISPATCHER.get(data.comparator)

        if not comparator_cls:
            ctx.logger.error(f"Unknown comparator: {data.comparator}")
            return

        comparator_config = (
            getattr(settings, data.comparator.value.replace("-", "_"), None)
            if comparator_cls.config_model
            else None
        )

        comparator = (
            comparator_cls(comparator_config)
            if comparator_config
            else comparator_cls()
        )

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
            try:
                link = next(
                    (
                        al
                        for al in catalog_record.authority_links
                        if al.base == data.target_base
                    ),
                    None,
                )

                if link is None:
                    ctx.logger.info(
                        f"No authority link found for {catalog_record.id} "
                        f"to base {data.target_base}"
                    )
                    continue

                result = await comparator.run(
                    MarcRecord.from_mrc(catalog_record.marc),
                    MarcRecord.from_mrc(link.authority_record.marc),
                )

                comparison = Comparison.find(
                    ctx.db_session,
                    catalog_record.id,
                    data.comparator.value,
                    link.authority_record.id,
                )

                if comparison:
                    comparison.result = result.model_dump()
                else:
                    comparison = Comparison(
                        main_record_id=catalog_record.id,
                        comparator=data.comparator.value,
                        other_record_id=link.authority_record.id,
                        result=result.model_dump(),
                    )

                comparison.save(ctx.db_session)

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

from typing import List

from marc_comparator.comparators import COMPARATOR_DISPATCHER
from marcdantic import MarcRecord

from adapters.tasks import ManagedTask
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.settings import Settings, SettingsScope

from .models import ComparisonSettings, ComparisonTaskData


async def compare_records(task_id: str) -> None:
    async with ManagedTask(task_id=task_id) as ctx:
        progress_interval = ctx.task_settings.progress_update_interval
        batch_size = ctx.task_settings.indexing_batch_size

        data = ComparisonTaskData.model_validate(ctx.task.data)
        settings = Settings.get(
            ctx.db_session,
            SettingsScope.Comparison,
            ComparisonSettings,
        )

        if not settings:
            raise ValueError("Comparison settings not found")

        comparator_cls = COMPARATOR_DISPATCHER.get(data.comparator)

        if not comparator_cls:
            raise ValueError(f"Unknown comparator: {data.comparator}")

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

        progress = 0
        reindex_batch: List[CatalogRecord] = []

        async for catalog_record in CatalogRecord.get_by_query(
            ctx.db_session, data.query
        ):
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
                ctx.db_session, catalog_record.id, link.authority_record.id
            )

            if comparison:
                comparison.result = result.model_dump()
            else:
                comparison = Comparison(
                    main_record_id=catalog_record.id,
                    other_record_id=link.authority_record.id,
                    result=result.model_dump(),
                )

            comparison.save(ctx.db_session)

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

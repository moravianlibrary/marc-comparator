from adapters.lock_server import get_active_locks
from adapters.marc_sectors import _decompressor, write_records_to_sector
from adapters.tasks import ManagedTask, handle_batch_progress_snippet, handle_final_batch_snippet
from entities.catalog_record import CatalogRecord
from entities.marc_sector import MarcRecordIndex, MarcSector


async def refresh_analytics(task_id: str) -> None:
    """Rebuild the catalog_records_analytics table from source tables."""
    async with ManagedTask(task_id=task_id) as ctx:
        ctx.logger.info("Rebuilding analytics table...")
        from catalog_records.analytics import rebuild_all

        rebuild_all(ctx.db_session)
        ctx.logger.info("Analytics table rebuilt successfully.")


async def cleanup_stale_locks(task_id: str) -> None:
    """Remove stale lock entries from Redis active_locks set."""
    async with ManagedTask(task_id=task_id) as ctx:
        ctx.logger.info("Cleaning up stale locks...")
        active = get_active_locks()
        ctx.logger.info(f"Active locks after cleanup: {len(active)}")


async def compact_sectors(task_id: str) -> None:
    """Rewrite MARC sectors to eliminate gaps from deleted records."""
    async with ManagedTask(task_id=task_id) as ctx:
        sectors = [
            (s.base, s.sector_id, s.record_count)
            for s in ctx.db_session.query(
                MarcSector.base, MarcSector.sector_id, MarcSector.record_count
            )
            .order_by(MarcSector.base, MarcSector.sector_id)
            .all()
        ]

        ctx.total = sum(rc for _, _, rc in sectors)
        ctx.logger.info(f"Found {len(sectors)} sectors to check for compaction.")

        for base, sector_id, record_count in sectors:
            indexes = (
                ctx.db_session.query(MarcRecordIndex)
                .filter(
                    MarcRecordIndex.base == base,
                    MarcRecordIndex.sector_id == sector_id,
                )
                .order_by(MarcRecordIndex.system_number)
                .all()
            )

            sector = ctx.db_session.get(MarcSector, (base, sector_id))
            if sector is None:
                ctx.progress += record_count
                ctx.update_progress()
                continue

            raw = _decompressor.decompress(sector.data)

            records: dict[str, bytes] = {}
            for idx in indexes:
                marc_bytes = raw[idx.offset_in_sector : idx.offset_in_sector + idx.record_length]
                records[idx.system_number] = marc_bytes

            if len(records) != sector.record_count:
                ctx.logger.info(
                    f"Compacting sector {base}/{sector_id}: "
                    f"{sector.record_count} stored -> {len(records)} live records"
                )

                if len(records) == 0:
                    ctx.db_session.delete(sector)
                else:
                    write_records_to_sector(ctx.db_session, base, sector_id, records)

                ctx.cycle_session()

            ctx.progress += record_count
            ctx.update_progress()

        handle_final_batch_snippet(ctx)

        ctx.logger.info(f"Compaction complete. Processed {ctx.progress} records.")


#: Records whose MARC is read in one go. They are walked in id order, so a
#: window mostly falls inside one or two sectors and is read as such.
REBUILD_WINDOW = 200


async def rebuild_search_vectors(task_id: str) -> None:
    """Rebuild search_text for all catalog records from their MARC data."""
    from collections import defaultdict

    from marcdantic import MarcRecord

    from adapters.marc_sectors import read_marc_many
    from adapters.pipelining import chunks

    async with ManagedTask(task_id=task_id) as ctx:
        record_ids = [r[0] for r in ctx.db_session.query(CatalogRecord.id).all()]
        ctx.total = len(record_ids)
        ctx.logger.info(f"Rebuilding search vectors for {ctx.total} records...")

        for window in chunks(record_ids, REBUILD_WINDOW):
            records = [ctx.db_session.get(CatalogRecord, record_id) for record_id in window]
            present = [record for record in records if record is not None]

            by_base: defaultdict[str, list[str]] = defaultdict(list)
            for record in present:
                by_base[record.base].append(record.system_number)
            marc_of = {
                (base, system_number): marc
                for base, system_numbers in by_base.items()
                for system_number, marc in read_marc_many(
                    ctx.db_session, base, system_numbers
                ).items()
            }

            for record in records:
                if record is None:
                    handle_batch_progress_snippet(ctx)
                    continue

                marc_bytes = marc_of.get((record.base, record.system_number))
                if marc_bytes:
                    try:
                        marc = MarcRecord.from_mrc(marc_bytes)
                        record.update_search_text_from(marc)
                    except Exception as e:
                        ctx.logger.warning(
                            f"Failed to rebuild search for "
                            f"{record.base}/{record.system_number}: {e}"
                        )

                handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(f"Search vector rebuild complete. Processed {ctx.progress} records.")

from collections.abc import Sequence

from marcdantic import MarcRecord

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
    """Rebuild search_text for all catalog records from their MARC data.

    Nothing here holds an ORM instance across a record, because
    ``handle_batch_progress_snippet`` commits and cycles the session every
    ``commit_interval`` of them — the rule ``CatalogRecord.warm`` states.
    Holding a window of them, which this did, meant that the first cycle
    landing inside a window detached every record after it and the next read
    of ``record.base`` raised ``DetachedInstanceError``. With a window of 200
    and a commit interval of 500 that is the third window: the task died 0.5%
    in, every time it was run.

    So the window is walked twice. The first pass reads the three columns it
    needs as plain tuples, which survive a cycle, and batches the MARC read by
    sector from them. The second looks each record up again by id — answered
    from the identity map while the window is warm, and from the database
    after a cycle has emptied it.
    """

    from collections import defaultdict

    from adapters.marc_sectors import read_marc_many, read_stored_marc
    from adapters.pipelining import chunks

    async with ManagedTask(task_id=task_id) as ctx:
        record_ids = [r[0] for r in ctx.db_session.query(CatalogRecord.id).all()]
        ctx.total = len(record_ids)
        ctx.logger.info(f"Rebuilding search vectors for {ctx.total} records...")

        for window in chunks(record_ids, REBUILD_WINDOW):
            located = {
                row.id: (row.base, row.system_number)
                for row in ctx.db_session.query(
                    CatalogRecord.id, CatalogRecord.base, CatalogRecord.system_number
                )
                .filter(CatalogRecord.id.in_(window))
                .all()
            }

            by_base: defaultdict[str, list[str]] = defaultdict(list)
            for base, system_number in located.values():
                by_base[base].append(system_number)
            marc_of = {
                (base, system_number): marc
                for base, system_numbers in by_base.items()
                for system_number, marc in read_marc_many(
                    ctx.db_session, base, system_numbers
                ).items()
            }

            CatalogRecord.warm(ctx.db_session, window)

            for record_id in window:
                where = located.get(record_id)
                record = ctx.db_session.get(CatalogRecord, record_id) if where else None
                if record is None or where is None:
                    # Deleted between listing the ids and getting here.
                    handle_batch_progress_snippet(ctx)
                    continue

                marc_bytes = marc_of.get(where)
                if marc_bytes:
                    try:
                        record.update_search_text_from(read_stored_marc(marc_bytes))
                    except Exception as e:
                        ctx.logger.warning(
                            f"Failed to rebuild search for {where[0]}/{where[1]}: {e}"
                        )

                # Commits and cycles the session on its own schedule; `record`
                # must not be touched after this.
                handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)

        ctx.logger.info(f"Search vector rebuild complete. Processed {ctx.progress} records.")


async def rescore_comparisons(task_id: str) -> None:
    """Recompute every stored comparison and link confidence from the MARC.

    Scores are stored, and the scale they are on has changed: from a 0-1
    similarity laid over the scoring engine's output to the engine's own
    numbers read as a 0-15 match, bigger being better. A stored 0.9 and a
    stored 9.0 are both valid readings of their own scale, so nothing can tell
    them apart by value — which is why this exists.

    It recomputes rather than converts. The old scale came out of two curves in
    series, the second of which was applied per field against a cap it guessed
    at, so the per-field and per-subfield numbers cannot be inverted even in
    principle. Recomputing gets all three levels right, is exact (a recomputed
    score matched all 600 stored ones in a sample), and is idempotent — running
    it twice is the same as running it once.

    Both halves need doing because a link's confidence *is* a comparator score:
    both linkers report ``comparison.overall_score`` as the confidence, and the
    floors they compare it against have moved with the scale.

    Shaped the way ``CatalogRecord.warm`` describes, and for the reason it
    gives: ``ManagedTask`` commits and cycles the session every
    ``commit_interval`` records, so nothing here holds an ORM instance across
    a window. Keys are collected up front, each window is warmed into the
    session in three queries, and every row is then read back out of the
    identity map. Holding the rows instead cost a 2 GiB worker.
    """

    from collections import defaultdict

    from sqlalchemy import select, tuple_

    from adapters.marc_sectors import read_marc_many, read_stored_marc
    from adapters.pipelining import chunks
    from comparison.tasks import load_comparator
    from entities.authority_link import AuthorityLink
    from entities.comparison import Comparison

    async with ManagedTask(task_id=task_id) as ctx:
        comparator = load_comparator(ctx.db_session)
        if not comparator:
            ctx.logger.error("Comparator could not be initialized")
            return

        comparison_keys = [
            (row.main_record_id, row.comparator, row.base, row.other_record_id)
            for row in ctx.db_session.query(
                Comparison.main_record_id,
                Comparison.comparator,
                Comparison.base,
                Comparison.other_record_id,
            ).all()
        ]
        link_keys = [
            (row.main_record_id, row.base, row.rank, row.authority_base, row.authority_sysno)
            for row in ctx.db_session.query(
                AuthorityLink.main_record_id,
                AuthorityLink.base,
                AuthorityLink.rank,
                AuthorityLink.authority_base,
                AuthorityLink.authority_sysno,
            )
            .filter(AuthorityLink.confidence.isnot(None))
            .filter(AuthorityLink.authority_sysno.isnot(None))
            .all()
        ]
        ctx.total = len(comparison_keys) + len(link_keys)
        ctx.logger.info(
            f"Rescoring {len(comparison_keys)} comparisons and {len(link_keys)} link confidences..."
        )

        # One window per session cycle, so a window is never split across one
        # and every lookup in it is answered from a warm identity map.
        window_size = max(1, ctx.task_settings.commit_interval)

        def warm(entity: type, keys: Sequence[tuple]) -> None:
            """Load a window of rows into the session by composite key.

            The same trick as ``CatalogRecord.warm``, for entities keyed by
            more than one column: one query fills the identity map, and the
            ``Session.get`` calls below are then answered from it. The result
            is deliberately discarded — holding it is the thing that must not
            happen here.
            """

            if not keys:
                return

            columns = tuple(entity.__mapper__.primary_key)
            ctx.db_session.execute(
                select(entity).where(tuple_(*columns).in_([tuple(key) for key in keys]))
            ).scalars().all()

        def marc_for(pairs: set[tuple[str, str]]) -> dict[tuple[str, str], MarcRecord]:
            """Read and parse both sides of a window's pairs, by sector."""
            by_base: defaultdict[str, list[str]] = defaultdict(list)
            for base, system_number in pairs:
                by_base[base].append(system_number)

            out: dict[tuple[str, str], MarcRecord] = {}
            for base, system_numbers in by_base.items():
                for system_number, raw in read_marc_many(
                    ctx.db_session, base, sorted(set(system_numbers))
                ).items():
                    try:
                        out[(base, system_number)] = read_stored_marc(raw)
                    except Exception as e:
                        ctx.logger.warning(f"Unreadable MARC for {base}/{system_number}: {e}")
            return out

        def marc_of(record_ids: Sequence[str]) -> dict[str, MarcRecord]:
            """This window's records, keyed by catalogue id."""
            records = {
                record_id: ctx.db_session.get(CatalogRecord, record_id)
                for record_id in set(record_ids)
            }
            marc = marc_for({(r.base, r.system_number) for r in records.values() if r is not None})
            return {
                record_id: marc[(record.base, record.system_number)]
                for record_id, record in records.items()
                if record is not None and (record.base, record.system_number) in marc
            }

        rescored_comparisons = 0
        for window in chunks(comparison_keys, window_size):
            warm(Comparison, [key[:3] for key in window])
            CatalogRecord.warm(
                ctx.db_session, [key[0] for key in window] + [key[3] for key in window]
            )
            marc = marc_of([key[0] for key in window] + [key[3] for key in window])

            for main_record_id, comparator_name, base, other_record_id in window:
                ours = marc.get(main_record_id)
                theirs = marc.get(other_record_id)
                row = ctx.db_session.get(Comparison, (main_record_id, comparator_name, base))
                if row is None or ours is None or theirs is None:
                    ctx.logger.warning(
                        f"No MARC for one side of {main_record_id}/{base}; left as it was"
                    )
                    handle_batch_progress_snippet(ctx)
                    continue

                try:
                    row.result = (await comparator.run(ours, theirs)).model_dump()
                    row.save(ctx.db_session, commit=False)
                    rescored_comparisons += 1
                except Exception as e:
                    ctx.logger.error(f"Failed rescoring {main_record_id}/{base}: {e}")

                # Commits and cycles the session on its own schedule; nothing
                # loaded above may be touched after this.
                handle_batch_progress_snippet(ctx)

        rescored_links = 0
        for window in chunks(link_keys, window_size):
            warm(AuthorityLink, [key[:3] for key in window])
            CatalogRecord.warm(ctx.db_session, [key[0] for key in window])
            marc = marc_of([key[0] for key in window])
            theirs_by_key = marc_for({(key[3], key[4]) for key in window if key[3] and key[4]})

            for main_record_id, base, rank, authority_base, authority_sysno in window:
                ours = marc.get(main_record_id)
                theirs = theirs_by_key.get((authority_base, authority_sysno))
                row = ctx.db_session.get(AuthorityLink, (main_record_id, base, rank))
                if row is None or ours is None or theirs is None:
                    # A candidate harvested before its MARC was kept, or a
                    # record since deleted. Leaving the old number is wrong on
                    # the new scale, but inventing one is worse.
                    ctx.logger.warning(
                        f"No MARC for one side of link "
                        f"{main_record_id}/{base}#{rank}; left as it was"
                    )
                    handle_batch_progress_snippet(ctx)
                    continue

                try:
                    row.confidence = (await comparator.run(ours, theirs)).overall_score
                    row.save(ctx.db_session, commit=False)
                    rescored_links += 1
                except Exception as e:
                    ctx.logger.error(f"Failed rescoring link {main_record_id}/{base}#{rank}: {e}")

                handle_batch_progress_snippet(ctx)

        handle_final_batch_snippet(ctx)
        ctx.logger.info(
            f"Rescoring complete: {rescored_comparisons} comparisons, "
            f"{rescored_links} link confidences."
        )

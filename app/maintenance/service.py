from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from entities.task import Task, TaskSchema, TaskType


async def refresh_analytics(
    created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Refreshing analytics",
            type=TaskType.RefreshAnalytics,
            created_by=created_by,
        ),
        db_session,
    )


async def cleanup_stale_locks(
    created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Cleaning up stale locks",
            type=TaskType.CleanupStaleLocks,
            created_by=created_by,
        ),
        db_session,
    )


async def compact_sectors(
    created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Compacting MARC sectors",
            type=TaskType.CompactSectors,
            created_by=created_by,
        ),
        db_session,
    )


async def rebuild_search_vectors(
    created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Rebuilding search vectors",
            type=TaskType.RebuildSearchVectors,
            created_by=created_by,
        ),
        db_session,
    )

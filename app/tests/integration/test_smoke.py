from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from adapters.database import DatabaseSession
from adapters.indexer import indexer_session as indexer_session_ctx
from adapters.lock_server import one_at_a_time_lock
from adapters.tasks import enqueue_task
from auth.models import TokenData
from entities.task import Task, TaskType


@pytest.mark.asyncio
async def test_database_session_smoke(db_session: DatabaseSession):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


@pytest.mark.asyncio
async def test_elasticsearch_smoke(indexer_session):
    """
    Basic smoke test to ensure Elasticsearch container
    and indexer connection works.
    """

    async with indexer_session_ctx() as indexer_session:
        #  Health check
        health = await indexer_session.cluster.health()
        assert "status" in health
        assert health["status"] in {"green", "yellow"}

        # Index a simple document
        index_name = "test-index"
        doc_id = str(uuid4())
        doc = {"message": "hello world", "id": doc_id}

        await indexer_session.index(index=index_name, id=doc_id, document=doc)

        # Retrieve the document
        retrieved = await indexer_session.get(index=index_name, id=doc_id)
        assert retrieved["_source"]["message"] == "hello world"

        # Delete it
        await indexer_session.delete(index=index_name, id=doc_id)

        # Verify deletion
        with pytest.raises(Exception):
            await indexer_session.get(index=index_name, id=doc_id)

        # Cleanup the index
        await indexer_session.indices.delete(
            index=index_name, ignore_unavailable=True
        )


@pytest.mark.asyncio
async def test_one_at_a_time_lock(lock_server_client):
    """
    Smoke test for one_at_a_time_lock context manager.
    Ensures that only one task can acquire the lock at a time.
    """

    lock_name = "test-lock"

    # First task acquires the lock
    with one_at_a_time_lock(lock_name) as acquired1:
        assert acquired1 is True

        # Second task cannot acquire the lock immediately (non-blocking)
        with one_at_a_time_lock(lock_name, blocking=False) as acquired2:
            assert acquired2 is False

    # After first lock context exits, lock should be available
    with one_at_a_time_lock(lock_name) as acquired3:
        assert acquired3 is True


@pytest.mark.asyncio
async def test_admin_user_smoke(user: TokenData):
    """
    Smoke test for the admin_user fixture.
    Ensures that the fixture provides a valid user.
    """
    assert user is not None
    assert user.user_id == "12345678-1234-4678-9abc-1234567890ab"


@pytest.mark.asyncio
async def test_client_smoke(client: AsyncClient):
    """Basic smoke test for the tasks_client fixture."""
    response = await client.get("/not-found")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tasks_client_smoke(
    db_session: DatabaseSession,
    indexer_session,
    user: TokenData,
    tasks_client,
):
    """Basic smoke test for the tasks_client fixture."""
    # Create a test task
    task = Task(
        name="Test Task",
        type=TaskType.SyncRecords,
        created_by=user.user_id,
        data={"base": "TEST"},
    )

    # Enqueue the task
    async with indexer_session_ctx() as _:
        await enqueue_task(task, db_session)


@pytest.mark.asyncio
async def test_aleph_client_registry_smoke(
    aleph_client_registry,
):
    """
    Basic smoke test for the AlephClientRegistry fixture.
    Ensures that the fixture provides a valid registry
    with at least one registered client.
    """
    from adapters.aleph_client_registry import AlephClientRegistry

    assert AlephClientRegistry.get("TEST") is not None

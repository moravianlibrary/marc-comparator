from uuid import uuid4

import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from adapters.lock_server import one_at_a_time_lock
from adapters.tasks import enqueue_task
from auth.models import TokenData
from entities.task import Task, TaskType


@pytest.mark.asyncio
async def test_elasticsearch_smoke(indexer_session):
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
    lock_name = "test-lock"

    with one_at_a_time_lock(lock_name) as lock1:
        assert lock1 is not None

        with one_at_a_time_lock(lock_name, blocking=False) as lock2:
            assert lock2 is None

    with one_at_a_time_lock(lock_name) as lock3:
        assert lock3 is not None


@pytest.mark.asyncio
async def test_tasks_client_smoke(
    db_session: DatabaseSession,
    indexer_session,
    user: TokenData,
    tasks_client,
):
    task = Task(
        name="Test Task",
        type=TaskType.SyncRecords,
        created_by=user.user_id,
        data={"base": "TEST"},
    )
    await enqueue_task(task, db_session)


@pytest.mark.asyncio
async def test_aleph_client_registry_smoke(aleph_client_registry):
    from adapters.aleph_client_registry import AlephClientRegistry

    assert AlephClientRegistry.get("TEST") is not None

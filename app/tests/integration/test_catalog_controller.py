import pytest
from aleph_nought import RecordStatus
from aleph_nought.oai.client import ListRecordResponse
from httpx import AsyncClient

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.database import DatabaseSession
from entities.catalog_record import CatalogRecord
from entities.task import Task
from tests.conftest import assert_response, load_test_record, FAKE_USER_ID


class TestEndpointsRO:
    @pytest.mark.asyncio
    async def test_fetch_record_success(
        self,
        db_session,
        indexer_session,
        lock_server_client,
        user,
        tasks_client,
        aleph_client_registry,
        client: AsyncClient,
    ):
        assert_response(
            await client.post(
                "/catalog-records/fetch",
                json={"base": "TEST", "system_number": "123"},
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": "Fetch catalog record TEST-123",
                "type": "FetchRecord",
                "status": "Pending",
                "severity": "Info",
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
                "progress": 0.0,
                "traceback_lines": 0,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )

    @pytest.mark.asyncio
    async def test_sync_records_success(
        self,
        db_session,
        indexer_session,
        lock_server_client,
        user,
        tasks_client,
        aleph_client_registry,
        client: AsyncClient,
    ):
        assert_response(
            await client.post("/catalog-records/sync", json={"base": "TEST"}),
            200,
            {
                "task_id": "IGNORE",
                "name": "Sync records from catalog for base TEST",
                "type": "SyncRecords",
                "status": "Pending",
                "severity": "Info",
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
                "progress": 0.0,
                "traceback_lines": 0,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )


class TestTasks:
    @pytest.mark.asyncio
    async def test_fetch_record_success(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        test_marc = load_test_record("MZK01-001217709.mrc")._marc
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.get_record.return_value = type(
            "MarcRecord",
            (),
            {"_marc": test_marc},
        )()

        fake_task.data = {"base": "TEST", "system_number": "123"}
        db_session.commit()

        from catalog_records.tasks import fetch_record_task

        await fetch_record_task(str(fake_task.task_id))

        record = CatalogRecord.get(db_session, "TEST-123")
        assert record is not None
        assert record.base == "TEST"
        assert record.system_number == "123"
        assert record.marc == test_marc

    @pytest.mark.asyncio
    async def test_fetch_record_not_found(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.get_record.return_value = None

        fake_task.data = {"base": "TEST", "system_number": "NOT_FOUND"}
        db_session.commit()

        from catalog_records.tasks import fetch_record_task

        await fetch_record_task(str(fake_task.task_id))

    @pytest.mark.asyncio
    async def test_fetch_record_oai_unavailable(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = False

        fake_task.data = {"base": "TEST", "system_number": "123"}
        db_session.commit()

        from catalog_records.tasks import fetch_record_task

        await fetch_record_task(str(fake_task.task_id))

    @pytest.mark.asyncio
    async def test_sync_records_success(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        test_marc_1 = load_test_record("MZK01-001217709.mrc")._marc
        test_marc_2 = load_test_record("MZK01-001217729.mrc")._marc
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.list_records.return_value = [
            ListRecordResponse(
                "TEST",
                "123",
                RecordStatus.Active,
                type("Record", (), {"_marc": test_marc_1})(),
            ),
            ListRecordResponse(
                "TEST",
                "456",
                RecordStatus.Active,
                type("Record", (), {"_marc": test_marc_2})(),
            ),
            ListRecordResponse("TEST", "789", RecordStatus.Deleted, None),
            ListRecordResponse("TEST", "000", RecordStatus.Active, None),
            ListRecordResponse("TEST", "999", RecordStatus.Failed, None),
        ]

        fake_task.data = {"base": "TEST"}
        db_session.commit()

        from catalog_records.tasks import records_sync_task

        await records_sync_task(str(fake_task.task_id), "catalog_sync_TEST", 1)

        record1 = CatalogRecord.get(db_session, "TEST-123")
        assert record1 is not None
        assert record1.base == "TEST"
        assert record1.system_number == "123"
        assert record1.marc == test_marc_1

        record2 = CatalogRecord.get(db_session, "TEST-456")
        assert record2 is not None
        assert record2.base == "TEST"
        assert record2.system_number == "456"
        assert record2.marc == test_marc_2

    @pytest.mark.asyncio
    async def test_sync_records_with_deleted_existing_record(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        """Syncing a deleted record that exists locally should mark it deleted."""
        test_marc = load_test_record("MZK01-001217709.mrc")._marc

        # Pre-create the record
        existing = CatalogRecord(
            base="TEST", system_number="123", marc=test_marc
        )
        existing.save(db_session)
        assert existing.deleted is False

        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.list_records.return_value = [
            ListRecordResponse("TEST", "123", RecordStatus.Deleted, None),
        ]

        fake_task.data = {"base": "TEST"}
        db_session.commit()

        from catalog_records.tasks import records_sync_task

        await records_sync_task(str(fake_task.task_id), "catalog_sync_TEST", 1)

        # ManagedTask uses its own DB session, so re-query
        updated = CatalogRecord.get(db_session, "TEST-123")
        assert updated.deleted is True

    @pytest.mark.asyncio
    async def test_sync_records_with_from_date(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        """Sync with a from_date should pass the formatted date to OAI."""
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.list_records.return_value = []

        fake_task.data = {
            "base": "TEST",
            "from_date": "2024-01-15T10:00:00Z",
        }
        db_session.commit()

        from catalog_records.tasks import records_sync_task

        await records_sync_task(str(fake_task.task_id), "catalog_sync_TEST", 1)

        client.OAI.list_records.assert_called_once_with(
            "2024-01-15T10:00:00Z", None
        )

    @pytest.mark.asyncio
    async def test_sync_records_oai_unavailable(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = False

        fake_task.data = {"base": "TEST"}
        db_session.commit()

        from catalog_records.tasks import records_sync_task

        await records_sync_task(str(fake_task.task_id), "catalog_sync_TEST", 1)

        # Should not attempt to list records
        client.OAI.list_records.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_batch_of_records_success(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        test_marc_1 = load_test_record("MZK01-001217709.mrc")._marc
        test_marc_2 = load_test_record("MZK01-001217729.mrc")._marc

        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.get_record.side_effect = [
            type("MarcRecord", (), {"_marc": test_marc_1})(),
            type("MarcRecord", (), {"_marc": test_marc_2})(),
        ]

        fake_task.type = "FetchBatchOfRecords"
        fake_task.data = {
            "per_base": [
                {"base": "TEST", "system_numbers": ["111", "222"]},
            ]
        }
        db_session.commit()

        from catalog_records.tasks import fetch_batch_of_records_task

        await fetch_batch_of_records_task(str(fake_task.task_id))

        record1 = CatalogRecord.get(db_session, "TEST-111")
        assert record1 is not None
        assert record1.marc == test_marc_1

        record2 = CatalogRecord.get(db_session, "TEST-222")
        assert record2 is not None
        assert record2.marc == test_marc_2

    @pytest.mark.asyncio
    async def test_fetch_batch_record_not_found(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        """Batch fetch where one record is None should skip it gracefully."""
        test_marc = load_test_record("MZK01-001217709.mrc")._marc
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.get_record.side_effect = [
            type("MarcRecord", (), {"_marc": test_marc})(),
            None,  # second record not found
        ]

        fake_task.type = "FetchBatchOfRecords"
        fake_task.data = {
            "per_base": [
                {"base": "TEST", "system_numbers": ["111", "222"]},
            ]
        }
        db_session.commit()

        from catalog_records.tasks import fetch_batch_of_records_task

        await fetch_batch_of_records_task(str(fake_task.task_id))

        assert CatalogRecord.find(db_session, "TEST-111") is not None
        assert CatalogRecord.find_by_base_and_system_number(
            db_session, "TEST", "222"
        ) is None

    @pytest.mark.asyncio
    async def test_fetch_batch_oai_unavailable(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        """Batch fetch when OAI is unavailable should skip that base."""
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = False

        fake_task.type = "FetchBatchOfRecords"
        fake_task.data = {
            "per_base": [
                {"base": "TEST", "system_numbers": ["111"]},
            ]
        }
        db_session.commit()

        from catalog_records.tasks import fetch_batch_of_records_task

        await fetch_batch_of_records_task(str(fake_task.task_id))

        client.OAI.get_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_batch_with_exception(
        self,
        db_session: DatabaseSession,
        indexer_session,
        lock_server_client,
        user,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        """Batch fetch should handle per-record exceptions gracefully."""
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.get_record.side_effect = RuntimeError("Network error")

        fake_task.type = "FetchBatchOfRecords"
        fake_task.data = {
            "per_base": [
                {"base": "TEST", "system_numbers": ["111"]},
            ]
        }
        db_session.commit()

        from catalog_records.tasks import fetch_batch_of_records_task

        # Should not raise
        await fetch_batch_of_records_task(str(fake_task.task_id))


class TestCatalogEndpoints:
    @pytest.mark.asyncio
    async def test_get_marc_record_not_found(
        self,
        db_session,
        indexer_session,
        user,
        client: AsyncClient,
    ):
        assert_response(
            await client.get("/catalog-records/TEST/999/marc"),
            404,
            {"detail": "Catalog record TEST-999 not found."},
        )

    @pytest.mark.asyncio
    async def test_get_marc_record_deleted(
        self,
        db_session: DatabaseSession,
        indexer_session,
        user,
        client: AsyncClient,
    ):
        """Deleted records should return 404."""
        test_marc = load_test_record("MZK01-001217709.mrc")._marc
        record = CatalogRecord(
            base="TEST", system_number="123", marc=test_marc, deleted=True
        )
        record.save(db_session)

        assert_response(
            await client.get("/catalog-records/TEST/123/marc"),
            404,
            {"detail": "Catalog record TEST-123 not found."},
        )

    @pytest.mark.asyncio
    async def test_get_marc_record_success(
        self,
        db_session: DatabaseSession,
        indexer_session,
        user,
        client: AsyncClient,
    ):
        test_marc = load_test_record("MZK01-001217709.mrc")._marc
        record = CatalogRecord(
            base="TEST", system_number="123", marc=test_marc
        )
        record.save(db_session)

        response = await client.get("/catalog-records/TEST/123/marc")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_batch_endpoint(
        self,
        db_session,
        indexer_session,
        lock_server_client,
        user,
        tasks_client,
        aleph_client_registry,
        client: AsyncClient,
    ):
        assert_response(
            await client.post(
                "/catalog-records/fetch-batch",
                json={
                    "per_base": [
                        {"base": "TEST", "system_numbers": ["111", "222"]},
                    ]
                },
            ),
            200,
            {
                "name": "Fetching batch of 2 catalog records from 1 bases",
                "type": "FetchBatchOfRecords",
                "status": "Pending",
            },
            exclude_field_paths={
                ("task_id",),
                ("created_at",),
                ("severity",),
                ("created_by",),
                ("started_at",),
                ("finished_at",),
                ("progress",),
                ("traceback_lines",),
            },
        )

    @pytest.mark.asyncio
    async def test_sync_records_lock_contention(
        self,
        db_session,
        indexer_session,
        lock_server_client,
        user,
        tasks_client,
        aleph_client_registry,
        client: AsyncClient,
    ):
        """Concurrent sync for the same base should fail with 409."""
        from adapters.lock_server import one_at_a_time_lock

        # Acquire the lock first
        with one_at_a_time_lock("catalog_sync_TEST") as lock:
            assert lock is not None

            # Now try to sync — should get 409 conflict
            assert_response(
                await client.post(
                    "/catalog-records/sync", json={"base": "TEST"}
                ),
                409,
                {
                    "detail": "Sync task is already running for base TEST."
                },
            )

    @pytest.mark.asyncio
    async def test_reindex_records_endpoint(
        self,
        db_session,
        indexer_session,
        user,
        tasks_client,
        client: AsyncClient,
    ):
        response = await client.post(
            "/catalog-records/reindex",
            json={"match_all": {}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Reindex catalog records"
        assert body["type"] == "ReindexRecords"
        assert body["status"] == "Pending"

    @pytest.mark.asyncio
    async def test_set_records_visibility_endpoint(
        self,
        db_session,
        indexer_session,
        user,
        tasks_client,
        client: AsyncClient,
    ):
        response = await client.post(
            "/catalog-records/visibility",
            json={"query": {"match_all": {}}, "visible": False},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "SetRecordsVisibility"

    @pytest.mark.asyncio
    async def test_process_records_endpoint(
        self,
        db_session,
        indexer_session,
        user,
        tasks_client,
        client: AsyncClient,
    ):
        response = await client.post(
            "/catalog-records/process",
            json={"match_all": {}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Process catalog records"
        assert body["type"] == "ProcessRecords"

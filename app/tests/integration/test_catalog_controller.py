import pytest
from aleph_nought import RecordStatus
from aleph_nought.oai.client import ListRecordResponse
from esorm import NotFoundError
from httpx import AsyncClient

from adapters.aleph_client_registry import AlephClientRegistry
from adapters.database import DatabaseSession
from entities.catalog_record import CatalogRecord, CatalogRecordSchema
from entities.task import Task
from tests.integration.conftest import assert_response


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "lock_server_client",
    "client",
    "user",
    "tasks_client",
    "aleph_client_registry",
)
class TestEndpointsRO:
    @pytest.mark.asyncio
    async def test_fetch_record_success(self, client: AsyncClient):
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
                "has_data": True,
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )

    # TODO: Add check so that invalid base raises error
    # @pytest.mark.asyncio
    # async def test_fetch_record_invalid_base(self, client: AsyncClient):
    #     response = await client.post(
    #         "/catalog-records/fetch",
    #         json={"base": "INVALID", "system_number": "123"},
    #     )
    #     assert response.status_code == 500
    #     assert response.json() == {
    #         "detail": "Aleph client for base 'INVALID' not found."
    #     }

    @pytest.mark.asyncio
    async def test_sync_records_success(self, client: AsyncClient):
        assert_response(
            await client.post("/catalog-records/sync", json={"base": "TEST"}),
            200,
            {
                "task_id": "IGNORE",
                "name": "Sync records from catalog for base TEST",
                "type": "SyncRecords",
                "status": "Pending",
                "has_data": True,
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )

    # TODO: Add check so that invalid base raises error
    # @pytest.mark.asyncio
    # async def test_sync_records_invalid_base(self, client: AsyncClient):
    #     response = await client.post("/catalog-records/sync",
    #       json={"base": "INVALID"})
    #     assert response.status_code == 500
    #     assert response.json() == {
    #         "detail": "Aleph client for base 'INVALID' not found."
    #     }


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "lock_server_client",
    "user",
    "aleph_client_registry",
)
class TestTasks:
    @pytest.mark.asyncio
    async def test_fetch_record_success(
        self,
        db_session: DatabaseSession,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.get_record.return_value = type(
            "MarcRecord",
            (),
            {"_marc": b"<record>Test</record>"},
        )()

        fake_task.data = {"base": "TEST", "system_number": "123"}
        db_session.commit()

        from catalog_records.tasks import fetch_record_task

        await fetch_record_task(str(fake_task.task_id))

        record = CatalogRecord.get(db_session, "TEST-123")
        assert record is not None
        assert record.base == "TEST"
        assert record.system_number == "123"
        assert record.marc == b"<record>Test</record>"

        record_in_index = await CatalogRecordSchema.get(record.id)
        assert record_in_index is not None
        assert record_in_index.base == "TEST"
        assert record_in_index.system_number == "123"

    @pytest.mark.asyncio
    async def test_fetch_record_not_found(
        self,
        db_session: DatabaseSession,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.get_record.return_value = None

        fake_task.data = {"base": "TEST", "system_number": "NOT_FOUND"}
        db_session.commit()

        from catalog_records.tasks import fetch_record_task

        with pytest.raises(Exception) as exc_info:
            await fetch_record_task(str(fake_task.task_id))

        assert (
            str(exc_info.value)
            == "Record with system number 'NOT_FOUND' not found"
        )

    @pytest.mark.asyncio
    async def test_fetch_record_oai_unavailable(
        self,
        db_session: DatabaseSession,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = False

        fake_task.data = {"base": "TEST", "system_number": "123"}
        db_session.commit()

        from catalog_records.tasks import fetch_record_task

        with pytest.raises(Exception) as exc_info:
            await fetch_record_task(str(fake_task.task_id))

        assert str(exc_info.value) == "OAI service is not available"

    @pytest.mark.asyncio
    async def test_sync_records_success(
        self,
        db_session: DatabaseSession,
        aleph_client_registry: AlephClientRegistry,
        fake_task: Task,
    ):
        client = aleph_client_registry.get("TEST")
        client.OAI.is_available.return_value = True
        client.OAI.list_records.return_value = [
            ListRecordResponse(
                "TEST",
                "123",
                RecordStatus.Active,
                type("Record", (), {"_marc": b"<record>1</record>"})(),
            ),
            ListRecordResponse(
                "TEST",
                "456",
                RecordStatus.Active,
                type("Record", (), {"_marc": b"<record>2</record>"})(),
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
        assert record1.marc == b"<record>1</record>"

        record2 = CatalogRecord.get(db_session, "TEST-456")
        assert record2 is not None
        assert record2.base == "TEST"
        assert record2.system_number == "456"
        assert record2.marc == b"<record>2</record>"

        record1_in_index = await CatalogRecordSchema.get(record1.id)
        assert record1_in_index is not None
        assert record1_in_index.base == "TEST"
        assert record1_in_index.system_number == "123"

        record2_in_index = await CatalogRecordSchema.get(record2.id)
        assert record2_in_index is not None
        assert record2_in_index.base == "TEST"
        assert record2_in_index.system_number == "456"

        assert await CatalogRecordSchema.get("TEST-123") is not None
        assert await CatalogRecordSchema.get("TEST-456") is not None

        for id in ["TEST-789", "TEST-000", "TEST-999"]:
            with pytest.raises(NotFoundError) as exc_info:
                await CatalogRecordSchema.get(id)
            assert str(exc_info.value) == f"Document with id {id} not found"

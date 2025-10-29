import json

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
    "client",
    "user",
    "tasks_client",
)
class TestEndpointsRO:
    @pytest.mark.asyncio
    async def test_get_settings_schema(self, client: AsyncClient):
        with open(
            "tests/integration/data/authority_linking_setttings.schema.json",
            "r",
        ) as f:
            expected_schema = json.load(f)

        assert_response(
            await client.get("/authority-linking/settings-schema"),
            200,
            expected_schema,
        )

    @pytest.mark.asyncio
    async def test_set_settings(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/authority-linking/settings",
                json={
                    "enabled_linkers": ["knihovny-cz"],
                    "knihovny_cz": {
                        "api_url": "https://api.knihovny.cz/v1/",
                        "mappings": [
                            {
                                "base": "MZK01",
                                "id_template": "mzk.MZK01-{system_number}",
                                "pattern": r"^mzk\.MZK01-(\d{9})$",
                            },
                            {
                                "base": "MZK03",
                                "id_template": "mzk.MZK03-{system_number}",
                                "pattern": r"^mzk\.MZK03-(\d{9})$",
                            },
                            {
                                "base": "SKC",
                                "id_template": "caslin.SKC01-{system_number}",
                                "pattern": r"^caslin\.SKC01-(\d{9})$",
                            },
                        ],
                    },
                },
            ),
            200,
            {
                "enabled_linkers": ["knihovny-cz"],
                "knihovny_cz": {
                    "api_url": "https://api.knihovny.cz/v1/",
                    "mappings": [
                        {
                            "base": "MZK01",
                            "id_template": "mzk.MZK01-{system_number}",
                            "pattern": r"^mzk\.MZK01-(\d{9})$",
                        },
                        {
                            "base": "MZK03",
                            "id_template": "mzk.MZK03-{system_number}",
                            "pattern": r"^mzk\.MZK03-(\d{9})$",
                        },
                        {
                            "base": "SKC",
                            "id_template": "caslin.SKC01-{system_number}",
                            "pattern": r"^caslin\.SKC01-(\d{9})$",
                        },
                    ],
                },
            },
        )

    @pytest.mark.asyncio
    async def test_authority_linking(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/authority-linking/task",
                json={"target_base": "SKC", "query": {"match_all": {}}},
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": "Authority linking for base 'SKC'",
                "type": "AuthorityLinking",
                "status": "Pending",
                "has_data": True,
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )

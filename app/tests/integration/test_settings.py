import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from tests.integration.conftest import assert_response, load_test_json


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "client",
    "user",
    "tasks_client",
)
class TestTasksSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_settings_schema(self, client: AsyncClient):
        assert_response(
            await client.get("/settings/tasks/AuthorityLinking/schema"),
            200,
            load_test_json("authority_linking_settings.schema.json"),
        )

    @pytest.mark.asyncio
    async def test_get_settings_not_found(self, client: AsyncClient):
        assert_response(
            await client.get("/settings/tasks/AuthorityLinking"),
            404,
            {"detail": "Settings for scope 'AuthorityLinking' not found."},
        )

    @pytest.mark.asyncio
    async def test_get_settings(
        self, db_session: DatabaseSession, client: AsyncClient
    ):
        from authority_linking.models import AuthorityLinkingSettings
        from entities.settings import Settings, SettingsScope

        test_settings = load_test_json("authority_linking_settings.json")

        Settings.save(
            db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings.model_validate(test_settings),
            AuthorityLinkingSettings,
        )

        assert_response(
            await client.get("/settings/tasks/AuthorityLinking"),
            200,
            test_settings,
        )

    @pytest.mark.asyncio
    async def test_set_settings(self, client: AsyncClient):
        test_settings = load_test_json("authority_linking_settings.json")

        assert_response(
            await client.post(
                "/settings/tasks/AuthorityLinking", json=test_settings
            ),
            200,
            test_settings,
        )

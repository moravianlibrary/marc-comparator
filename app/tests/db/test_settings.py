import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from entities.settings import Settings, SettingsScope
from tests.conftest import assert_response, load_test_json


# ---- Test data helpers ----

def _catalog_settings_data():
    return {
        "clients": [
            {
                "base": "MZK01",
                "host": "https://aleph.mzk.cz",
                "endpoint": "OAI",
                "system_number_pattern": r"\d{9}",
                "oai_sets": ["MZK01-VDK"],
                "oai_identifier_template": "oai:aleph.mzk.cz:{base}-{doc_number}",
            }
        ]
    }


def _task_settings_data():
    return {
        "progress_update_interval": 200,
        "commit_interval": 1000,
    }


def _process_records_settings_data():
    return {
        "target_bases": ["MZK01"],
        "authority_linkers": ["knihovny-cz"],
        "validators": ["kramerius-links"],
    }


class TestTasksSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_settings_not_found(
        self, db_session, user, client: AsyncClient
    ):
        assert_response(
            await client.get("/settings/record-tools/authority-linkers"),
            404,
            {"detail": "Settings for scope 'authority-linkers' not found."},
        )

    @pytest.mark.asyncio
    async def test_get_settings(
        self, db_session: DatabaseSession, user, client: AsyncClient
    ):
        from authority_linking.models import AuthorityLinkingSettings

        test_settings = load_test_json("authority_linking_settings.json")

        Settings.save(
            db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings.model_validate(test_settings),
            AuthorityLinkingSettings,
        )

        assert_response(
            await client.get("/settings/record-tools/authority-linkers"),
            200,
            test_settings,
        )

    @pytest.mark.asyncio
    async def test_set_settings(
        self, db_session, user, client: AsyncClient
    ):
        test_settings = load_test_json("authority_linking_settings.json")

        assert_response(
            await client.post(
                "/settings/record-tools/authority-linkers", json=test_settings
            ),
            200,
            test_settings,
        )


class TestComparisonSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_comparison_settings_not_found(
        self, db_session, user, client: AsyncClient
    ):
        assert_response(
            await client.get("/settings/record-tools/comparators"),
            404,
            {"detail": "Settings for scope 'comparators' not found."},
        )

    @pytest.mark.asyncio
    async def test_set_and_get_comparison_settings(
        self, db_session, user, client: AsyncClient
    ):
        test_settings = load_test_json("comparison_settings.json")

        set_response = await client.post(
            "/settings/record-tools/comparators", json=test_settings
        )
        assert set_response.status_code == 200
        saved = set_response.json()

        # Get back should return the same expanded data
        assert_response(
            await client.get("/settings/record-tools/comparators"),
            200,
            saved,
        )


class TestValidationSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_validation_settings_not_found(
        self, db_session, user, client: AsyncClient
    ):
        assert_response(
            await client.get("/settings/record-tools/validators"),
            404,
            {"detail": "Settings for scope 'validators' not found."},
        )

    @pytest.mark.asyncio
    async def test_set_and_get_validation_settings(
        self, db_session, user, client: AsyncClient
    ):
        test_settings = load_test_json("validation_settings.json")

        set_response = await client.post(
            "/settings/record-tools/validators", json=test_settings
        )
        assert set_response.status_code == 200
        saved = set_response.json()

        assert_response(
            await client.get("/settings/record-tools/validators"),
            200,
            saved,
        )


class TestCatalogSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_catalog_settings_not_found(
        self, db_session, user, client: AsyncClient
    ):
        assert_response(
            await client.get("/settings/system/catalog"),
            404,
            {"detail": "Settings for scope 'catalog' not found."},
        )

    @pytest.mark.asyncio
    async def test_set_and_get_catalog_settings(
        self, db_session, user, client: AsyncClient
    ):
        data = _catalog_settings_data()

        set_response = await client.post(
            "/settings/system/catalog", json=data
        )
        assert set_response.status_code == 200
        saved = set_response.json()

        # Get returns the full expanded model with defaults
        assert_response(
            await client.get("/settings/system/catalog"),
            200,
            saved,
        )


class TestTaskSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_task_settings_not_found(
        self, db_session, user, client: AsyncClient
    ):
        assert_response(
            await client.get("/settings/system/tasks"),
            404,
            {"detail": "Settings for scope 'tasks' not found."},
        )

    @pytest.mark.asyncio
    async def test_set_and_get_task_settings(
        self, db_session, user, client: AsyncClient
    ):
        data = _task_settings_data()

        assert_response(
            await client.post("/settings/system/tasks", json=data),
            200,
            data,
        )

        assert_response(
            await client.get("/settings/system/tasks"),
            200,
            data,
        )


class TestProcessRecordsSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_process_records_settings_not_found(
        self, db_session, user, client: AsyncClient
    ):
        assert_response(
            await client.get("/settings/record-tools/process-records"),
            404,
            {"detail": "Settings for scope 'process-records' not found."},
        )

    @pytest.mark.asyncio
    async def test_set_and_get_process_records_settings(
        self, db_session, user, client: AsyncClient
    ):
        data = _process_records_settings_data()

        assert_response(
            await client.post(
                "/settings/record-tools/process-records", json=data
            ),
            200,
            data,
        )

        assert_response(
            await client.get("/settings/record-tools/process-records"),
            200,
            data,
        )


class TestSettingsUpdate:
    @pytest.mark.asyncio
    async def test_update_existing_settings(
        self, db_session, user, client: AsyncClient
    ):
        """Setting settings twice should update, not create a duplicate."""
        data_v1 = _task_settings_data()
        data_v2 = {
            "progress_update_interval": 50,
            "commit_interval": 250,
        }

        await client.post("/settings/system/tasks", json=data_v1)

        assert_response(
            await client.post("/settings/system/tasks", json=data_v2),
            200,
            data_v2,
        )

        # Verify the update persisted
        assert_response(
            await client.get("/settings/system/tasks"),
            200,
            data_v2,
        )


class TestSettingsService:
    def test_get_settings_part(self, db_session, user):
        from settings.service import get_settings_part
        from tasks.models import TaskSettings

        Settings.save(
            db_session,
            SettingsScope.Tasks,
            TaskSettings(progress_update_interval=42, commit_interval=100),
            TaskSettings,
        )

        result = get_settings_part(SettingsScope.Tasks, "progress_update_interval", db_session)
        assert result == 42

    def test_get_settings_part_not_found(self, db_session, user):
        from settings.exceptions import SettingsPartNotFoundError
        from settings.service import get_settings_part
        from tasks.models import TaskSettings

        Settings.save(
            db_session,
            SettingsScope.Tasks,
            TaskSettings(),
            TaskSettings,
        )

        with pytest.raises(SettingsPartNotFoundError):
            get_settings_part(SettingsScope.Tasks, "nonexistent_field", db_session)

    def test_get_settings_part_by_alias(self, db_session, user):
        """get_settings_part should resolve field aliases."""
        from settings.service import get_settings_part
        from validation.models import ValidationSettings

        test_settings = load_test_json("validation_settings.json")
        Settings.save(
            db_session,
            SettingsScope.Validation,
            ValidationSettings.model_validate(test_settings),
            ValidationSettings,
        )

        # "kramerius-links" is the alias for "kramerius_links"
        result = get_settings_part(
            SettingsScope.Validation, "kramerius-links", db_session
        )
        assert result is not None

    def test_get_settings_scope_not_found_raises(self, db_session, user):
        from settings.exceptions import SettingsNotFoundError
        from settings.service import get_settings

        with pytest.raises(SettingsNotFoundError):
            get_settings(SettingsScope.Catalog, db_session)

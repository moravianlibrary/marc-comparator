from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from entities.settings import Settings, SettingsScope
from tests.conftest import assert_response, load_test_json


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_ok(
        self,
        db_session,
        lock_server_client,
        client: AsyncClient,
    ):
        """Health endpoint returns 200 when DB and lock server are reachable."""
        with patch("system.service.redis_client", lock_server_client):
            response = await client.get("/system/health")
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "ok"
            assert "details" not in body

    @pytest.mark.asyncio
    async def test_health_no_auth_required(
        self,
        db_session,
        lock_server_client,
        client: AsyncClient,
    ):
        """Health endpoint works without authentication (no user fixture)."""
        with patch("system.service.redis_client", lock_server_client):
            response = await client.get("/system/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_db_down(
        self,
        db_session,
        lock_server_client,
        client: AsyncClient,
    ):
        """Health endpoint returns 503 when DB is unreachable."""
        with patch("system.service.DatabaseSession.execute", side_effect=Exception("DB down")):
            response = await client.get("/system/health")
            assert response.status_code == 503
            body = response.json()
            assert body["status"] == "error"
            assert body["details"]["db"] == "error"

    @pytest.mark.asyncio
    async def test_health_lock_server_down(
        self,
        db_session,
        lock_server_client,
        client: AsyncClient,
    ):
        """Health endpoint returns 503 when lock server is unreachable."""
        with patch("system.service.redis_client") as mock_redis:
            mock_redis.ping.side_effect = Exception("Redis down")
            response = await client.get("/system/health")
            assert response.status_code == 503
            body = response.json()
            assert body["status"] == "error"
            assert body["details"]["lock_server"] == "error"


class TestSystemInfoEndpoint:
    @pytest.mark.asyncio
    async def test_get_system_info_no_settings(
        self,
        db_session,
        user,
        client: AsyncClient,
    ):
        """System info should return empty lists when no settings configured."""
        response = await client.get("/system/info")
        assert response.status_code == 200
        body = response.json()
        assert body["configured_bases"] == []
        assert body["enabled_authority_linkers"] == []
        assert body["enabled_validators"] == []
        assert "system_version" in body
        assert "system_commit" in body
        assert body["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_get_system_info_with_catalog_settings(
        self,
        db_session: DatabaseSession,
        user,
        client: AsyncClient,
    ):
        """System info should list available bases from catalog settings."""
        from catalog_records.models import CatalogSettings

        catalog_data = {
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
        Settings.save(
            db_session,
            SettingsScope.Catalog,
            CatalogSettings.model_validate(catalog_data),
            CatalogSettings,
        )

        response = await client.get("/system/info")
        assert response.status_code == 200
        body = response.json()
        assert body["configured_bases"] == ["MZK01"]

    @pytest.mark.asyncio
    async def test_get_system_info_with_validation_settings(
        self,
        db_session: DatabaseSession,
        user,
        client: AsyncClient,
    ):
        """System info should list enabled validators from validation settings."""
        from validation.models import ValidationSettings

        test_settings = load_test_json("validation_settings.json")
        Settings.save(
            db_session,
            SettingsScope.Validation,
            ValidationSettings.model_validate(test_settings),
            ValidationSettings,
        )

        response = await client.get("/system/info")
        assert response.status_code == 200
        body = response.json()
        assert "kramerius-links" in body["enabled_validators"]

    @pytest.mark.asyncio
    async def test_get_system_info_unauthenticated(
        self,
        db_session,
        client: AsyncClient,
    ):
        """System info endpoint requires authentication."""
        assert_response(
            await client.get("/system/info"),
            401,
            {"detail": "Not authenticated"},
        )


class TestSystemServiceUnit:
    def test_get_configured_bases_no_settings(self, db_session, user):
        from system.service import get_configured_bases

        result = get_configured_bases(db_session)
        assert result == []

    def test_get_enabled_validators_no_settings(self, db_session, user):
        from system.service import get_enabled_validators

        result = get_enabled_validators(db_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_enabled_authority_linkers_no_settings(self, db_session, user):
        from system.service import get_enabled_authority_linkers

        result = await get_enabled_authority_linkers(db_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_enabled_authority_linkers_with_settings(
        self, db_session: DatabaseSession, user
    ):
        from authority_linking.models import AuthorityLinkingSettings
        from system.service import get_enabled_authority_linkers

        test_settings = load_test_json("authority_linking_settings.json")
        Settings.save(
            db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings.model_validate(test_settings),
            AuthorityLinkingSettings,
        )

        # Patch the linker's get_target_bases to avoid actual HTTP calls
        with patch("system.service.AUTHORITY_LINKER_DISPATCHER") as mock_dispatcher:
            mock_linker_cls = AsyncMock()
            mock_linker_cls.get_target_bases = AsyncMock(return_value=["MZK01", "MZK03"])
            mock_linker_cls.config_model.model_validate.return_value = object()
            mock_dispatcher.get.return_value = mock_linker_cls

            result = await get_enabled_authority_linkers(db_session)
            assert len(result) == 1
            assert result[0].name == "knihovny-cz"
            assert result[0].target_bases == ["MZK01", "MZK03"]

    def test_get_enabled_validators_with_settings(self, db_session: DatabaseSession, user):
        from system.service import get_enabled_validators
        from validation.models import ValidationSettings

        test_settings = load_test_json("validation_settings.json")
        Settings.save(
            db_session,
            SettingsScope.Validation,
            ValidationSettings.model_validate(test_settings),
            ValidationSettings,
        )

        result = get_enabled_validators(db_session)
        assert "kramerius-links" in result

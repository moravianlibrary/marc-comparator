import os
import time
from typing import List

from marc_comparator.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
)

from sqlalchemy import text

from adapters.database import DatabaseSession
from adapters.lock_server import get_active_locks, lock_server_client as redis_client
from authority_linking.models import AuthorityLinkingSettings
from catalog_records.models import CatalogSettings
from entities.settings import Settings, SettingsScope
from settings.models import SETTINGS_MODEL_DISPATCHER

from .models import AuthorityLinkerInfo, HealthStatus, SystemInfo

START_TS = time.time()


def get_settings(scope: SettingsScope, db_session: DatabaseSession):
    model_cls = SETTINGS_MODEL_DISPATCHER.get(scope)
    if not model_cls:
        return None

    settings = Settings.get(db_session, scope, model_cls)
    return settings


def get_configured_bases(db_session: DatabaseSession) -> List[str]:
    settings: CatalogSettings = get_settings(SettingsScope.Catalog, db_session)
    return [client.base for client in settings.clients] if settings else []


def _get_enabled_tools(
    db_session: DatabaseSession, scope: SettingsScope
) -> List[str]:
    settings = get_settings(scope, db_session)
    if not settings:
        return []

    enabled = []
    for name, value in settings.model_dump(by_alias=True).items():
        if value is not None:
            enabled.append(name)
    return enabled


async def get_enabled_authority_linkers(
    db_session: DatabaseSession,
) -> List[AuthorityLinkerInfo]:
    settings: AuthorityLinkingSettings = get_settings(
        SettingsScope.AuthorityLinking, db_session
    )

    if not settings:
        return []

    linkers = []
    for name, config_obj in settings.model_dump(by_alias=True).items():
        if config_obj is None:
            continue

        linker_enum = AuthorityLinker(name)
        linker_cls = AUTHORITY_LINKER_DISPATCHER.get(linker_enum)
        if not linker_cls:
            continue

        target_bases = await linker_cls.get_target_bases(
            linker_cls.config_model.model_validate(config_obj)
        )
        linkers.append(AuthorityLinkerInfo(name=name, target_bases=target_bases))

    return linkers


def get_enabled_validators(db_session: DatabaseSession) -> List[str]:
    return _get_enabled_tools(db_session, SettingsScope.Validation)


async def get_system_info(db_session: DatabaseSession) -> SystemInfo:
    from marc_comparator.validators.kramerius_links import (
        KrameriusLinksValidatorConfig,
    )

    # Build per-base kramerius_client_urls mapping
    kramerius_client_urls = {}

    # Get default URL from validator config
    default_url = None
    validation_settings = get_settings(SettingsScope.Validation, db_session)
    if validation_settings:
        data = validation_settings.model_dump(by_alias=True)
        kl_config = data.get("kramerius-links")
        if kl_config:
            cfg = KrameriusLinksValidatorConfig.model_validate(kl_config)
            default_url = cfg.kramerius_client_url

    # Get per-base overrides from catalog settings
    catalog_settings: CatalogSettings = get_settings(
        SettingsScope.Catalog, db_session
    )
    if catalog_settings:
        per_base = catalog_settings.kramerius_client_urls
        for client in catalog_settings.clients:
            url = per_base.get(client.base, default_url)
            if url:
                kramerius_client_urls[client.base] = url

    enabled_linkers = await get_enabled_authority_linkers(db_session)
    authority_bases = sorted(
        {base for linker in enabled_linkers for base in linker.target_bases}
    )

    return SystemInfo(
        system_version=os.getenv("SYSTEM_VERSION", "dev"),
        system_commit=os.getenv("SYSTEM_COMMIT", "dev"),
        uptime_seconds=time.time() - START_TS,
        configured_bases=get_configured_bases(db_session),
        authority_bases=authority_bases,
        enabled_authority_linkers=enabled_linkers,
        enabled_validators=get_enabled_validators(db_session),
        kramerius_client_urls=kramerius_client_urls,
    )


def check_health(db_session: DatabaseSession) -> HealthStatus:
    details = {}
    healthy = True

    try:
        db_session.execute(text("SELECT 1"))
        details["db"] = "ok"
    except Exception:
        details["db"] = "error"
        healthy = False

    try:
        redis_client.ping()
        details["lock_server"] = "ok"
    except Exception:
        details["lock_server"] = "error"
        healthy = False

    return HealthStatus(
        status="ok" if healthy else "error",
        details=details if not healthy else None,
    )


def get_locks() -> List[str]:
    return get_active_locks()

import os
import time

from marc_comparator.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
)
from marc_comparator.validators import VALIDATOR_DISPATCHER, Validator
from sqlalchemy import text

from adapters.database import DatabaseSession
from adapters.lock_server import get_active_locks
from adapters.lock_server import lock_server_client as redis_client
from authority_linking.models import AuthorityLinkingSettings
from catalog_records.models import CatalogSettings
from comparison import UsedComparator, UsedComparatorClass
from comparison.models import ComparisonSettings
from entities.settings import Settings, SettingsSchema, SettingsSchemaT, SettingsScope
from settings.models import SETTINGS_MODEL_DISPATCHER
from validation.models import ValidationSettings

from .models import AuthorityLinkerInfo, HealthStatus, SystemInfo

START_TS = time.time()


def get_settings(
    scope: SettingsScope,
    model: type[SettingsSchemaT],
    db_session: DatabaseSession,
) -> SettingsSchemaT | None:
    """Stored settings for a scope, or None when the scope is unknown or unset."""
    if SETTINGS_MODEL_DISPATCHER.get(scope) is None:
        return None

    return Settings.get(db_session, scope, model)


def get_settings_for_scope(
    scope: SettingsScope, db_session: DatabaseSession
) -> SettingsSchema | None:
    """Same, for a scope only known at runtime — the model comes from the dispatcher."""
    model_cls = SETTINGS_MODEL_DISPATCHER.get(scope)
    if model_cls is None:
        return None

    return Settings.get(db_session, scope, model_cls)


def get_configured_bases(db_session: DatabaseSession) -> list[str]:
    settings = get_settings(SettingsScope.Catalog, CatalogSettings, db_session)
    return [client.base for client in settings.clients] if settings else []


def _get_enabled_tools(db_session: DatabaseSession, scope: SettingsScope) -> list[str]:
    settings = get_settings_for_scope(scope, db_session)
    if not settings:
        return []

    enabled = []
    for name, value in settings.model_dump(by_alias=True).items():
        if value is not None:
            enabled.append(name)
    return enabled


async def get_enabled_authority_linkers(
    db_session: DatabaseSession,
) -> list[AuthorityLinkerInfo]:
    settings = get_settings(SettingsScope.AuthorityLinking, AuthorityLinkingSettings, db_session)

    if not settings:
        return []

    # The scope also carries settings that are not a linker configuration, such
    # as the threshold deciding between the two linking stages. Only fields
    # named after a known linker describe one.
    linker_names = {linker.value for linker in AuthorityLinker}

    linkers = []
    for name, config_obj in settings.model_dump(by_alias=True).items():
        if config_obj is None or name not in linker_names:
            continue

        linker_enum = AuthorityLinker(name)
        linker_cls = AUTHORITY_LINKER_DISPATCHER.get(linker_enum)
        if not linker_cls:
            continue

        if linker_cls.config_model is None:
            continue

        target_bases = await linker_cls.get_target_bases(
            linker_cls.config_model.model_validate(config_obj)
        )
        linkers.append(AuthorityLinkerInfo(name=name, target_bases=target_bases))

    return linkers


def get_enabled_validators(db_session: DatabaseSession) -> list[str]:
    return _get_enabled_tools(db_session, SettingsScope.Validation)


def get_report_capable_validators(db_session: DatabaseSession) -> list[str]:
    """Enabled validators that implement ``generate_report``."""
    capable = []
    for name in get_enabled_validators(db_session):
        try:
            validator_cls = VALIDATOR_DISPATCHER.get(Validator(name))
        except ValueError:
            continue
        if validator_cls and validator_cls.can_generate_report:
            capable.append(name)
    return capable


def get_report_capable_comparator(db_session: DatabaseSession) -> str | None:
    """The enabled comparator's name, if it implements ``generate_report``."""
    settings = get_settings(SettingsScope.Comparison, ComparisonSettings, db_session)
    if not settings or settings.comparator is None:
        return None
    if not UsedComparatorClass.can_generate_report:
        return None
    return UsedComparator.value


async def get_system_info(db_session: DatabaseSession) -> SystemInfo:
    from marc_comparator.validators.kramerius_links import (
        KrameriusLinksValidatorConfig,
    )

    # Build per-base kramerius_client_urls mapping
    kramerius_client_urls = {}

    # Get default URL from validator config
    default_url = None
    validation_settings = get_settings(SettingsScope.Validation, ValidationSettings, db_session)
    if validation_settings:
        data = validation_settings.model_dump(by_alias=True)
        kl_config = data.get("kramerius-links")
        if kl_config:
            cfg = KrameriusLinksValidatorConfig.model_validate(kl_config)
            default_url = cfg.kramerius_client_url

    # Get per-base overrides from catalog settings
    catalog_settings = get_settings(SettingsScope.Catalog, CatalogSettings, db_session)
    if catalog_settings:
        per_base = catalog_settings.kramerius_client_urls
        for client in catalog_settings.clients:
            url = per_base.get(client.base, default_url)
            if url:
                kramerius_client_urls[client.base] = url

    enabled_linkers = await get_enabled_authority_linkers(db_session)
    authority_bases = sorted({base for linker in enabled_linkers for base in linker.target_bases})

    return SystemInfo(
        system_version=os.getenv("SYSTEM_VERSION", "dev"),
        system_commit=os.getenv("SYSTEM_COMMIT", "dev"),
        uptime_seconds=time.time() - START_TS,
        configured_bases=get_configured_bases(db_session),
        authority_bases=authority_bases,
        enabled_authority_linkers=enabled_linkers,
        enabled_validators=get_enabled_validators(db_session),
        report_capable_validators=get_report_capable_validators(db_session),
        report_capable_comparator=get_report_capable_comparator(db_session),
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


def get_locks() -> list[str]:
    return get_active_locks()

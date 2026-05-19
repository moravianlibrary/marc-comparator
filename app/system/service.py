import os
import time
from typing import List

from marc_comparator.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
)

from adapters.database import DatabaseSession
from adapters.tasks import enqueue_task
from authority_linking.models import AuthorityLinkingSettings
from catalog_records.models import CatalogSettings
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.models import SETTINGS_MODEL_DISPATCHER

from .models import AuthorityLinkerInfo, SystemInfo

START_TS = time.time()


def get_settings(scope: SettingsScope, db_session: DatabaseSession):
    model_cls = SETTINGS_MODEL_DISPATCHER.get(scope)
    if not model_cls:
        return None

    settings = Settings.get(db_session, scope, model_cls)
    return settings


def get_available_bases(db_session: DatabaseSession) -> List[str]:
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


def get_enabled_comparators(db_session: DatabaseSession) -> List[str]:
    return _get_enabled_tools(db_session, SettingsScope.Comparison)


def get_enabled_validators(db_session: DatabaseSession) -> List[str]:
    return _get_enabled_tools(db_session, SettingsScope.Validation)


async def get_system_info(db_session: DatabaseSession) -> SystemInfo:
    return SystemInfo(
        system_version=os.getenv("SYSTEM_VERSION", "dev"),
        system_commit=os.getenv("SYSTEM_COMMIT", "dev"),
        uptime_seconds=time.time() - START_TS,
        available_bases=get_available_bases(db_session),
        enabled_authority_linkers=await get_enabled_authority_linkers(
            db_session
        ),
        enabled_comparators=get_enabled_comparators(db_session),
        enabled_validators=get_enabled_validators(db_session),
    )


async def recreate_indexes(
    created_by: str, db_session: DatabaseSession
) -> TaskSchema:
    return await enqueue_task(
        Task(
            name="Recreating indexes",
            type=TaskType.RecreateIndexes,
            created_by=created_by,
        ),
        db_session,
    )

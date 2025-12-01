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
from comparison.models import ComparisonSettings
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskSchema, TaskType
from settings.models import SETTINGS_MODEL_DISPATCHER
from validation.models import ValidationSettings

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


async def get_enabled_authority_linkers(
    db_session: DatabaseSession,
) -> AuthorityLinkerInfo:
    settings: AuthorityLinkingSettings = get_settings(
        SettingsScope.AuthorityLinking, db_session
    )

    if not settings:
        return []

    linkers = []

    if settings.knihovny_cz is not None:
        target_bases = await AUTHORITY_LINKER_DISPATCHER[
            AuthorityLinker.KnihovnyCz
        ].get_target_bases(settings.knihovny_cz)

        linkers.append(
            AuthorityLinkerInfo(name="knihovny-cz", target_bases=target_bases)
        )

    return linkers


def get_enabled_comparators(db_session: DatabaseSession) -> List[str]:
    settings: ComparisonSettings = get_settings(
        SettingsScope.Comparison, db_session
    )

    if not settings:
        return []

    comparators = []

    if settings.intiim is not None:
        comparators.append("intiim")

    return comparators


def get_enabled_validators(db_session: DatabaseSession) -> List[str]:
    settings: ValidationSettings = get_settings(
        SettingsScope.Validation, db_session
    )

    if not settings:
        return []

    validators = []

    if settings.kramerius_links is not None:
        validators.append("kramerius-links")

    return validators


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

from entities.settings import SettingsSchema


class PeriodicSyncBaseConfig(SettingsSchema):
    base: str
    enabled: bool = False
    interval_hours: int = 24


class PeriodicProcessingConfig(SettingsSchema):
    """Scheduled processing of records that no processing has covered yet.

    A sync clears ``processed_at`` on every record it changes, so "unprocessed"
    means new-or-changed — which makes this the natural follow-up to the
    harvest schedule above rather than a second full pass over the catalog.
    """

    enabled: bool = False
    interval_hours: int = 24


class PeriodicSyncSettings(SettingsSchema):
    """Scheduled record jobs: the per-base OAI harvest and the processing that
    follows it.

    Independent of CatalogSettings (which defines the available bases); this
    only says which of them are harvested on a schedule and how often.
    """

    bases: list[PeriodicSyncBaseConfig] = []
    processing: PeriodicProcessingConfig = PeriodicProcessingConfig()

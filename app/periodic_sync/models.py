from entities.settings import SettingsSchema


class PeriodicSyncBaseConfig(SettingsSchema):
    base: str
    enabled: bool = False
    interval_hours: int = 24


class PeriodicSyncSettings(SettingsSchema):
    """Per-base scheduled OAI harvest configuration.

    Independent of CatalogSettings (which defines the available bases); this
    only says which of them are harvested on a schedule and how often.
    """

    bases: list[PeriodicSyncBaseConfig] = []

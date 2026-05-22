from entities.settings import SettingsSchema


class PeriodicTaskConfig(SettingsSchema):
    enabled: bool = False
    interval_hours: int = 24


class MaintenanceSettings(SettingsSchema):
    task_cleanup: PeriodicTaskConfig = PeriodicTaskConfig()
    task_cleanup_max_age_days: int = 30
    sector_compaction: PeriodicTaskConfig = PeriodicTaskConfig()

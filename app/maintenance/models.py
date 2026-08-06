from entities.settings import SettingsSchema


class PeriodicTaskConfig(SettingsSchema):
    enabled: bool = False
    interval_hours: int = 24


class MaintenanceSettings(SettingsSchema):
    task_cleanup: PeriodicTaskConfig = PeriodicTaskConfig()
    task_cleanup_max_age_days: int = 30
    sector_compaction: PeriodicTaskConfig = PeriodicTaskConfig()
    # Reaper of tasks left stuck in Started after a worker died. Enabled by
    # default and runs hourly — it is the safety net for the acks_late
    # redelivery fix, so it should be on out of the box.
    orphan_reaper: PeriodicTaskConfig = PeriodicTaskConfig(enabled=True, interval_hours=1)

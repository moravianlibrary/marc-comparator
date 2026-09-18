from entities.settings import SettingsSchema


class PeriodicTaskConfig(SettingsSchema):
    enabled: bool = False
    interval_hours: int = 24


class MaintenanceSettings(SettingsSchema):
    # Housekeeping that every deployment wants: without them task rows and
    # half-empty sectors grow without bound. Daily is frequent enough that
    # neither ever has much to do.
    task_cleanup: PeriodicTaskConfig = PeriodicTaskConfig(enabled=True, interval_hours=24)
    task_cleanup_max_age_days: int = 30
    sector_compaction: PeriodicTaskConfig = PeriodicTaskConfig(enabled=True, interval_hours=24)
    # Reaper of tasks left stuck in Started after a worker died. Enabled by
    # default and runs hourly — it is the safety net for the acks_late
    # redelivery fix, so it should be on out of the box.
    orphan_reaper: PeriodicTaskConfig = PeriodicTaskConfig(enabled=True, interval_hours=1)

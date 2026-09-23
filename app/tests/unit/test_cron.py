"""Cron expressions in the schedule settings."""

import pytest
from celery.schedules import crontab

from adapters.cron import DAILY, HOURLY, CronExpression, parse_cron
from maintenance.models import MaintenanceSettings, PeriodicTaskConfig


class TestParsing:
    def test_reads_the_standard_field_order(self):
        # Standard cron is minute hour day-of-month month day-of-week. Getting
        # the order wrong would schedule a job for a plausible but wrong time.
        parsed = parse_cron("30 2 * * 1")

        assert parsed == crontab(minute="30", hour="2", day_of_week="1")

    def test_accepts_steps_and_lists(self):
        assert parse_cron("0 */6 * * *") == crontab(minute="0", hour="*/6")
        assert parse_cron("0 8,20 * * *") == crontab(minute="0", hour="8,20")

    @pytest.mark.parametrize(
        "expression",
        [
            "0 2 * *",
            "0 2 * * * *",
            "",
            "0 25 * * *",
            "0 2 * * funday",
            "every night",
        ],
    )
    def test_rejects_what_beat_could_not_run(self, expression: str):
        # beat reads these in a background process, so an expression it cannot
        # parse stops the job silently. Refusing it at the door is the point.
        with pytest.raises(ValueError):
            parse_cron(expression)

    def test_named_months_and_days_are_not_a_server_error(self):
        # celery raises KeyError rather than ValueError for an unknown name,
        # which would leave the API returning 500 instead of a rejected field.
        with pytest.raises(ValueError):
            parse_cron("0 2 * smarch *")


class TestValidatedField:
    def test_a_bad_expression_is_rejected_where_it_is_entered(self):
        with pytest.raises(ValueError):
            PeriodicTaskConfig(enabled=True, cron="0 99 * * *")

    def test_surrounding_whitespace_is_not_stored(self):
        assert PeriodicTaskConfig(cron="  0 3 * * *  ").cron == "0 3 * * *"


def test_maintenance_defaults_keep_their_cadence():
    settings = MaintenanceSettings()

    assert settings.task_cleanup.cron == DAILY
    assert settings.sector_compaction.cron == DAILY
    # The reaper is the safety net for redelivered tasks; it stays hourly.
    assert settings.orphan_reaper.cron == HOURLY


def test_cron_expression_type_is_exported_for_reuse():
    assert CronExpression is not None

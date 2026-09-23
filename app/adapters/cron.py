"""Cron expressions for the scheduled jobs.

A schedule given as an interval in hours can say "every six hours" but never
"at 02:00, when nobody is using the catalogue". A cron expression says both, so
that is what the settings carry.

The expression is validated where it is entered rather than where it is used.
Celery's beat process reads these entries in the background; an expression it
cannot parse there fails silently in a log nobody is watching, and the job just
never runs again.
"""

from __future__ import annotations

from typing import Annotated

from celery.schedules import crontab
from pydantic import AfterValidator

#: Every day at midnight.
DAILY = "0 0 * * *"
#: Every hour on the hour.
HOURLY = "0 * * * *"

CRON_FIELDS = 5


def parse_cron(expression: str) -> crontab:
    """Turn a five-field cron expression into a celery schedule.

    Celery parses each field itself and raises for anything it cannot read, so
    this adds only the field count and the argument order that standard cron
    uses: minute, hour, day of month, month, day of week.
    """

    fields = expression.split()
    if len(fields) != CRON_FIELDS:
        raise ValueError(
            f"Cron expression must have {CRON_FIELDS} fields "
            f"(minute hour day-of-month month day-of-week), got {len(fields)}: {expression!r}"
        )

    minute, hour, day_of_month, month_of_year, day_of_week = fields
    try:
        return crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )
    except (ValueError, KeyError) as error:
        # celery raises KeyError for an unknown month or weekday name, which
        # would reach the API as a 500 rather than a rejected field.
        raise ValueError(f"Invalid cron expression {expression!r}: {error}") from error


def _validate(expression: str) -> str:
    parse_cron(expression)
    return expression.strip()


#: A cron expression proven parseable at the point it is stored.
CronExpression = Annotated[str, AfterValidator(_validate)]

"""RedBeat reconciliation for per-plugin harvesting."""

from adapters.cron import DAILY
from adapters.redbeat_schedule import sync_entry

from .models import PluginHarvestSettings
from .registry import harvestable_plugins

ENTRY_PREFIX = "redbeat:plugin-harvest-"


def entry_name(plugin_name: str) -> str:
    return f"{ENTRY_PREFIX}{plugin_name}"


def sync_harvest_schedule(
    settings: PluginHarvestSettings,
    *,
    stale_plugin_names: set[str] | None = None,
) -> None:
    """Reconcile all discovered schedules and remove no-longer-known entries."""

    plugins = {plugin.name: plugin for plugin in harvestable_plugins()}
    for name in stale_plugin_names or set():
        if name not in plugins:
            # The placeholder values are irrelevant when disabled, but keep the
            # call valid even if an old malformed settings row is encountered.
            sync_entry(entry_name(name), "periodic_harvest_plugin", False, DAILY, args=[name])

    for name in plugins:
        config = settings.plugins.get(name)
        sync_entry(
            entry_name(name),
            "periodic_harvest_plugin",
            config.enabled if config else False,
            config.cron if config else DAILY,
            args=[name],
        )

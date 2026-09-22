from datetime import datetime

from sqlalchemy import TIMESTAMP, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from adapters.database import Base
from entities._operations import BaseOperationsMixin


class PluginHarvestState(Base, BaseOperationsMixin):
    """Per-plugin bookkeeping for harvested datasets.

    Deliberately plugin-agnostic: the host tracks *that* a plugin has harvested
    and at what schema version, never what the plugin actually stored. The rows
    the plugin wrote live in its own Postgres schema, which this table only
    names.
    """

    __tablename__ = "plugin_harvest_state"

    #: Registry name of the plugin, e.g. "kramerius-links".
    plugin: Mapped[str] = mapped_column(String, primary_key=True)

    #: Postgres schema holding this plugin's tables.
    schema_name: Mapped[str] = mapped_column(String)

    #: The plugin's harvest_schema_version at the time its tables were built.
    #: A plugin reporting a different value has its schema dropped and rebuilt.
    schema_version: Mapped[int] = mapped_column(Integer)

    #: Plugin-defined fingerprint of settings that determine the remote dataset.
    #: A mismatch forces a rebuild and prevents lookup against stale-source data.
    source_identity: Mapped[str] = mapped_column(String)

    #: Opaque value the plugin returned from its last successful harvest, handed
    #: back on the next run so it can fetch only what changed. Null means the
    #: next run is a full fetch.
    watermark: Mapped[str | None] = mapped_column(String, nullable=True)

    #: Records processed by the last successful run, for the operator's benefit.
    records: Mapped[int] = mapped_column(Integer, default=0)

    last_harvest_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

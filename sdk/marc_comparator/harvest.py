"""Contracts for plugins that keep a local copy of a remote dataset.

A validator or linker that would otherwise query a remote service once per
record can harvest that service into plugin-owned tables and answer locally.
The plugin owns its table definitions and queries; the host owns database
access, the assigned namespace, transactions, and scheduling.

SQLAlchemy is optional (``marc-comparator-sdk[storage]``). Runtime imports stay
out of this module so ordinary SDK and CLI use does not require it.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from sqlalchemy import Connection, MetaData


class HarvestProgress(Protocol):
    """Report completed work and, when known, the total amount of work."""

    def __call__(self, done: int, total: int | None = None) -> None: ...


type ConnectionFactory = Callable[[], AbstractContextManager[Connection]]


class HarvestStorageUnavailable(RuntimeError):
    """Bound storage became incompatible before a lookup could use it."""


@dataclass(frozen=True, slots=True)
class HarvestStorage:
    """A ready local dataset that a plugin may use for lookup.

    ``connection`` is a factory rather than a live connection. Each lookup (or
    bounded group of lookups) opens its own context, so plugin instances remain
    safe when application sessions are committed, closed, or used by another
    worker. The host only binds storage after checking that its successful
    source identity and schema version match the current plugin instance.
    """

    schema: str
    source_identity: str
    connection: ConnectionFactory


@dataclass(slots=True)
class HarvestContext:
    """Resources supplied by the host for one transactional harvest run."""

    connection: Connection
    schema: str
    progress: HarvestProgress
    watermark: str | None = None


class HarvestResult(BaseModel):
    """Outcome to publish atomically with the harvested rows."""

    watermark: str | None = None
    records: int = Field(default=0, ge=0)

    #: Rows the local copy holds once this run is published.
    #:
    #: ``records`` measures one run, which for an incremental harvest says
    #: nothing about the size of the copy: a run that touched a few thousand
    #: documents leaves an operator no way to tell whether the copy behind it
    #: holds a hundred thousand or ten million. A plugin that cannot count its
    #: own rows cheaply leaves this ``None`` and the host reports only the run.
    total_records: int | None = Field(default=None, ge=0)


class HarvestCapable:
    """Optional local-harvest capability shared by validators and linkers.

    Existing plugins inherit harmless defaults. A plugin opts in by setting
    ``needs_harvest = True`` and implementing the metadata, source identity,
    and harvest methods.
    """

    needs_harvest: bool = False
    harvest_schema_version: int = 1
    _harvest_storage: HarvestStorage | None = None

    @property
    def harvest_storage(self) -> HarvestStorage | None:
        """The compatible local dataset bound by the host, if one is ready."""

        return self._harvest_storage

    @property
    def harvest_ready(self) -> bool:
        """Whether this instance has a compatible local dataset for lookup."""

        return self._harvest_storage is not None

    def bind_harvest_storage(self, storage: HarvestStorage | None) -> None:
        """Bind a ready dataset, or ``None`` to retain remote lookup behavior."""

        self._harvest_storage = storage

    def harvest_source_identity(self) -> str:
        """Return a stable fingerprint for harvest-relevant configuration.

        Presentation-only settings should be omitted. Source URL, collection,
        credentials that change visible data, and similar inputs should be
        included. Harvest-capable plugins must override this method; the value
        itself is opaque to the host.
        """

        raise NotImplementedError

    @classmethod
    def harvest_metadata(cls, schema: str) -> MetaData:
        """Declare every table in the host-assigned ``schema``."""

        raise NotImplementedError

    async def harvest(self, ctx: HarvestContext) -> HarvestResult:
        """Populate plugin tables using the host-owned transaction in ``ctx``."""

        raise NotImplementedError

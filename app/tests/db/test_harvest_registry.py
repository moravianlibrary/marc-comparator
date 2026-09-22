from datetime import UTC, datetime

import pytest
from marc_comparator.harvest import HarvestCapable, HarvestContext, HarvestResult
from sqlalchemy import Column, Integer, MetaData, String, Table, insert, select, text
from sqlalchemy.orm import Session

from entities.plugin_harvest import PluginHarvestState
from entities.settings import SettingsScope
from harvest.registry import (
    HarvestablePlugin,
    HarvestAlreadyRunningError,
    acquire_harvest_lock,
    complete_harvest,
    dataset_is_ready,
    drop_schema,
    ensure_schema,
)
from validation.models import ValidationSettings


class FakeHarvest(HarvestCapable):
    needs_harvest = True
    harvest_schema_version = 1

    def harvest_source_identity(self) -> str:
        return "source-v1"

    @classmethod
    def harvest_metadata(cls, schema: str) -> MetaData:
        metadata = MetaData(schema=schema)
        Table(
            "records",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("value", String, nullable=False),
        )
        return metadata

    async def harvest(self, ctx: HarvestContext) -> HarvestResult:
        table = self.harvest_metadata(ctx.schema).tables[f"{ctx.schema}.records"]
        ctx.connection.execute(insert(table).values(id=1, value="published"))
        ctx.progress(1, 1)
        return HarvestResult(watermark="watermark-v1", records=1)


PLUGIN = HarvestablePlugin(
    "foundation-test", FakeHarvest, SettingsScope.Validation, ValidationSettings
)


@pytest.mark.db
@pytest.mark.asyncio
async def test_harvest_publication_and_failed_rebuild_are_atomic(
    db_session: Session,
):
    drop_schema(PLUGIN, db_session)
    db_session.commit()
    try:
        assert ensure_schema(PLUGIN, db_session, "source-v1") is True
        result = await FakeHarvest().harvest(
            HarvestContext(
                connection=db_session.connection(),
                schema=PLUGIN.schema_name,
                progress=lambda done, total=None: None,
            )
        )
        completed_at = datetime.now(UTC)
        complete_harvest(PLUGIN, db_session, result, "source-v1", completed_at=completed_at)
        db_session.commit()

        state = db_session.get(PluginHarvestState, PLUGIN.name)
        assert dataset_is_ready(PLUGIN, state, "source-v1") is True
        assert state is not None
        assert state.watermark == "watermark-v1"
        assert state.records == 1

        table = FakeHarvest.harvest_metadata(PLUGIN.schema_name).tables[
            f"{PLUGIN.schema_name}.records"
        ]
        assert db_session.execute(select(table.c.value)).scalar_one() == "published"
        db_session.rollback()

        FakeHarvest.harvest_schema_version = 2
        with pytest.raises(RuntimeError, match="simulated failure"):
            assert ensure_schema(PLUGIN, db_session, "source-v2") is True
            db_session.execute(insert(table).values(id=2, value="unpublished"))
            raise RuntimeError("simulated failure")
        db_session.rollback()

        FakeHarvest.harvest_schema_version = 1
        state = db_session.get(PluginHarvestState, PLUGIN.name)
        assert dataset_is_ready(PLUGIN, state, "source-v1") is True
        assert state is not None
        assert state.watermark == "watermark-v1"
        assert db_session.execute(select(table.c.value)).scalars().all() == ["published"]
        db_session.rollback()

        # A source-only rebuild also stays pending until the same transaction
        # publishes success, and rollback restores the prior ready source.
        assert ensure_schema(PLUGIN, db_session, "source-v2") is True
        pending = db_session.get(PluginHarvestState, PLUGIN.name)
        assert pending is not None
        assert pending.last_harvest_at is None
        assert pending.watermark is None
        db_session.rollback()
        restored = db_session.get(PluginHarvestState, PLUGIN.name)
        assert dataset_is_ready(PLUGIN, restored, "source-v1") is True
    finally:
        FakeHarvest.harvest_schema_version = 1
        db_session.rollback()
        drop_schema(PLUGIN, db_session)
        db_session.commit()


@pytest.mark.db
def test_harvest_advisory_lock_is_exclusive_for_the_transaction(db_engine):
    first = Session(db_engine)
    second = Session(db_engine)
    try:
        acquire_harvest_lock(PLUGIN, first)
        with pytest.raises(HarvestAlreadyRunningError, match="already running"):
            acquire_harvest_lock(PLUGIN, second)
        second.rollback()

        first.rollback()
        acquire_harvest_lock(PLUGIN, second)
    finally:
        first.rollback()
        second.rollback()
        first.close()
        second.close()


@pytest.mark.db
def test_drop_schema_does_not_commit(db_session: Session, mocker):
    db_session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{PLUGIN.schema_name}"'))
    db_session.commit()
    commit = mocker.spy(db_session, "commit")

    drop_schema(PLUGIN, db_session)

    assert commit.call_count == 0
    db_session.rollback()

import pytest
from httpx import AsyncClient
from marc_comparator.comparators import BaseComparator, RecordComparisonResult
from pytest_mock import MockerFixture

from adapters.database import DatabaseSession
from auth.models import TokenData
from comparison.models import ComparisonSettings, ComparisonTaskData
from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskType
from tasks.models import TaskSettings
from tests.conftest import (
    assert_response,
    create_catalog_record,
    load_test_json,
    load_test_record,
)


# --- Fixtures ---


@pytest.fixture(scope="function")
def comparison_settings(db_session: DatabaseSession) -> Settings:
    test_settings = load_test_json("comparison_settings.json")
    return Settings.save(
        db_session,
        SettingsScope.Comparison,
        ComparisonSettings.model_validate(test_settings),
        ComparisonSettings,
    )


@pytest.fixture(scope="function")
def main_catalog_record(
    db_session: DatabaseSession,
) -> CatalogRecord:
    return create_catalog_record(
        db_session, "MZK01", "000999001",
        load_test_record("MZK01-001217709.mrc"),
    )


@pytest.fixture(scope="function")
def authority_catalog_record(db_session: DatabaseSession) -> CatalogRecord:
    return create_catalog_record(
        db_session, "SKC", "000999001",
        load_test_record("MZK01-001217729.mrc"),
    )


@pytest.fixture(scope="function")
def authority_link(
    db_session: DatabaseSession,
    main_catalog_record: CatalogRecord,
    authority_catalog_record: CatalogRecord,
) -> AuthorityLink:
    AuthorityLink(
        main_record_id=main_catalog_record.id,
        linker="knihovny-cz",
        base="SKC",
        authority_record_id=authority_catalog_record.id,
        confidence=0.5,
    ).save(db_session)


@pytest.fixture(scope="function")
def task(db_session: DatabaseSession, user: TokenData) -> Task:
    return Task(
        name="Comparison test task",
        type=TaskType.CompareRecords,
        created_by=user.user_id,
        data=ComparisonTaskData(
            comparator="intiim",
            target_base="SKC",
        ).model_dump(mode="json"),
    ).save(db_session)


@pytest.fixture(scope="function")
def mock_comparator_result(mocker: MockerFixture) -> MockerFixture:
    class MockComparator(BaseComparator):
        async def run(self, record_a, record_b) -> RecordComparisonResult:
            return RecordComparisonResult(
                overall_score=0.9, summary="Mock comparison result"
            )

    return mocker.patch(
        "comparison.tasks.COMPARATOR_DISPATCHER",
        {"intiim": MockComparator},
    )


@pytest.fixture(scope="function")
def mock_no_comparator(mocker: MockerFixture) -> MockerFixture:
    return mocker.patch(
        "comparison.tasks.COMPARATOR_DISPATCHER",
        {},
    )


@pytest.fixture(scope="function")
def task_settings_one_by_one(db_session: DatabaseSession) -> TaskSettings:
    settings = TaskSettings(
        progress_update_interval=1,
        indexing_batch_size=1,
    )
    return Settings.save(
        db_session,
        SettingsScope.Tasks,
        settings,
        TaskSettings,
    )


@pytest.fixture(scope="function")
def comparison(
    db_session: DatabaseSession,
    main_catalog_record: CatalogRecord,
    authority_catalog_record: CatalogRecord,
) -> Comparison:
    return Comparison(
        main_record_id=main_catalog_record.id,
        comparator="intiim",
        base="SKC",
        other_record_id=authority_catalog_record.id,
        result={"overall_score": 0.9, "summary": "Mock comparison result"},
    ).save(db_session)


# --- Test classes ---


class TestComparisonEndpoints:
    @pytest.mark.asyncio
    async def test_comparison_task_creation(
        self,
        db_session,
        user,
        tasks_client,
        comparison_settings,
        client: AsyncClient,
    ):
        assert_response(
            await client.post(
                "/comparison/task",
                json={
                    "comparator": "intiim",
                    "target_base": "SKC",
                },
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": (
                    "Comparing records "
                    "against authority records from 'SKC' base "
                    "using intiim comparator"
                ),
                "type": "CompareRecords",
                "status": "Pending",
                "severity": "Info",
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
                "progress": 0.0,
                "traceback_lines": 0,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )


class TestComparisonTask:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        tasks_client,
        authority_link,
        comparison_settings,
        task: Task,
        mock_comparator_result,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "000999001"
                ).comparisons
            )
            == 1
        )


class TestComparisonTaskWithExistingComparison:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        tasks_client,
        authority_link,
        comparison_settings,
        task: Task,
        mock_comparator_result,
        comparison,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "000999001"
                ).comparisons
            )
            == 1
        )


class TestComparisonTaskWithoutExistingAuthorityLink:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        tasks_client,
        main_catalog_record,
        comparison_settings,
        task: Task,
        mock_comparator_result,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "000999001"
                ).comparisons
            )
            == 0
        )


class TestComparisonTaskNoSettingsFound:
    @pytest.mark.asyncio
    async def test_no_linker_settings_found(
        self,
        db_session,
        tasks_client,
        main_catalog_record,
        task: Task,
        mock_comparator_result,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)


class TestComparisonTaskNoComparatorFound:
    @pytest.mark.asyncio
    async def test_no_comparator_found(
        self,
        db_session,
        tasks_client,
        main_catalog_record,
        comparison_settings,
        task: Task,
        mock_no_comparator,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)


class TestComparisonTaskIndexingOneByOne:
    @pytest.mark.asyncio
    async def test_indexing_one_by_one(
        self,
        db_session,
        tasks_client,
        authority_link,
        comparison_settings,
        task: Task,
        mock_comparator_result,
        task_settings_one_by_one,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

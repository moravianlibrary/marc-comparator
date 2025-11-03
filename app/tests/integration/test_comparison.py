import pytest
import pytest_asyncio
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
from tests.integration.conftest import (
    assert_response,
    load_test_json,
    load_test_record,
)


@pytest.fixture(scope="class")
def comparison_settings(
    db_session: DatabaseSession,
) -> Settings:
    test_settings = load_test_json("comparison_settings.json")
    return Settings.save(
        db_session,
        SettingsScope.Comparison,
        ComparisonSettings.model_validate(test_settings),
        ComparisonSettings,
    )


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "client",
    "user",
    "tasks_client",
    "comparison_settings",
)
class TestComparisonEndpoints:
    @pytest.mark.asyncio
    async def test_comparison_task_creation(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/comparison/task",
                json={
                    "comparator": "rule-based",
                    "target_base": "SKC",
                    "query": {"match_all": {}},
                },
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": (
                    "Comparing records "
                    "against authority records from 'SKC' base "
                    "using rule-based comparator"
                ),
                "type": "CompareRecords",
                "status": "Pending",
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )


@pytest_asyncio.fixture(scope="class")
async def main_catalog_record(
    db_session: DatabaseSession, indexer_session
) -> CatalogRecord:
    record = CatalogRecord(
        base="MZK01",
        system_number="COMPARISON-TEST",
        marc=load_test_record("MZK01-001217709.mrc")._marc,
    ).save(db_session)
    db_session.flush()
    await record.index(wait_for=True)
    return record


@pytest.fixture(scope="class")
def authority_catalog_record(
    db_session: DatabaseSession,
) -> CatalogRecord:
    return CatalogRecord(
        base="SKC",
        system_number="COMPARISON-TEST",
        marc=load_test_record("MZK01-001217729.mrc")._marc,
    ).save(db_session)


@pytest.fixture(scope="class")
def authority_link(
    db_session: DatabaseSession,
    main_catalog_record: CatalogRecord,
    authority_catalog_record: CatalogRecord,
) -> AuthorityLink:
    AuthorityLink(
        main_record_id=main_catalog_record.id,
        authority_record_id=authority_catalog_record.id,
        confidence=0.5,
    ).save(db_session)


@pytest.fixture(scope="class")
def task(db_session: DatabaseSession, user: TokenData) -> Task:
    return Task(
        name="Comparison test task",
        type=TaskType.CompareRecords,
        created_by=user.user_id,
        data=ComparisonTaskData(
            comparator="rule-based",
            target_base="SKC",
            query={"query": {"match_all": {}}},
        ).model_dump(mode="json"),
    ).save(db_session)


@pytest.fixture(scope="class")
def mock_comparator_result(class_mocker: MockerFixture) -> MockerFixture:
    class MockComparator(BaseComparator):
        async def run(self, record_a, record_b) -> RecordComparisonResult:
            return RecordComparisonResult(
                overall_score=0.9, summary="Mock comparison result"
            )

    return class_mocker.patch(
        "comparison.tasks.COMPARATOR_DISPATCHER",
        {"rule-based": MockComparator},
    )


@pytest.fixture(scope="class")
def mock_no_comparator(class_mocker: MockerFixture) -> MockerFixture:
    return class_mocker.patch(
        "comparison.tasks.COMPARATOR_DISPATCHER",
        {},
    )


@pytest.fixture(scope="class")
def task_settings_one_by_one(db_session: DatabaseSession) -> TaskSettings:
    settings = TaskSettings(
        progress_update_interval=1,
        indexing_batch_size=1,
    )
    return Settings.save(
        db_session,
        SettingsScope.Task,
        settings,
        TaskSettings,
    )


@pytest.fixture(scope="class")
def comparison(
    db_session: DatabaseSession,
    main_catalog_record: CatalogRecord,
    authority_catalog_record: CatalogRecord,
) -> Comparison:
    return Comparison(
        main_record_id=main_catalog_record.id,
        other_record_id=authority_catalog_record.id,
        result={"overall_score": 0.9, "summary": "Mock comparison result"},
    ).save(db_session)


@pytest.mark.usefixtures(
    "tasks_client",
    "authority_link",
    "comparison_settings",
    "task",
    "mock_comparator_result",
)
class TestComparisonTask:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        task: Task,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "COMPARISON-TEST"
                ).comparisons
            )
            == 1
        )


@pytest.mark.usefixtures(
    "tasks_client",
    "authority_link",
    "comparison_settings",
    "task",
    "mock_comparator_result",
    "comparison",
)
class TestComparisonTaskWithExistingComparison:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        task: Task,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "COMPARISON-TEST"
                ).comparisons
            )
            == 1
        )


@pytest.mark.usefixtures(
    "tasks_client",
    "main_catalog_record",
    "comparison_settings",
    "task",
    "mock_comparator_result",
)
class TestComparisonTaskWithoutExistingAuthorityLink:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        task: Task,
    ):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "COMPARISON-TEST"
                ).comparisons
            )
            == 0
        )


@pytest.mark.usefixtures(
    "tasks_client",
    "main_catalog_record",
    "task",
    "mock_comparator_result",
)
class TestComparisonTaskNoSettingsFound:
    @pytest.mark.asyncio
    async def test_no_linker_settings_found(self, task: Task):
        from comparison.tasks import compare_records

        with pytest.raises(ValueError, match="Comparison settings not found"):
            await compare_records(task.task_id)


@pytest.mark.usefixtures(
    "tasks_client",
    "main_catalog_record",
    "comparison_settings",
    "task",
    "mock_no_comparator",
)
class TestComparisonTaskNoComparatorFound:
    @pytest.mark.asyncio
    async def test_no_linker_settings_found(self, task: Task):
        from comparison.tasks import compare_records

        with pytest.raises(ValueError, match="Unknown comparator: rule-based"):
            await compare_records(task.task_id)


@pytest.mark.usefixtures(
    "tasks_client",
    "authority_link",
    "comparison_settings",
    "task",
    "mock_comparator_result",
    "task_settings_one_by_one",
)
class TestComparisonTaskIndexingOneByOne:
    @pytest.mark.asyncio
    async def test_indexing_one_by_one(self, task: Task):
        from comparison.tasks import compare_records

        await compare_records(task.task_id)

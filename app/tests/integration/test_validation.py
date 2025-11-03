import pytest
import pytest_asyncio
from httpx import AsyncClient
from marc_comparator.validators import (
    BaseValidator,
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)
from pytest_mock import MockerFixture

from adapters.database import DatabaseSession
from auth.models import TokenData
from entities.catalog_record import CatalogRecord
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskType
from entities.validation import Validation
from tasks.models import TaskSettings
from tests.integration.conftest import (
    assert_response,
    load_test_json,
    load_test_record,
)
from validation.models import ValidationSettings, ValidationTaskData


@pytest.fixture(scope="class")
def validation_settings(
    db_session: DatabaseSession,
) -> Settings:
    test_settings = load_test_json("validation_settings.json")
    return Settings.save(
        db_session,
        SettingsScope.Validation,
        ValidationSettings.model_validate(test_settings),
        ValidationSettings,
    )


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "client",
    "user",
    "tasks_client",
    "validation_settings",
)
class TestValidationEndpoints:
    @pytest.mark.asyncio
    async def test_validation_task_creation(self, client: AsyncClient):
        assert_response(
            await client.post(
                "/validation/task",
                json={
                    "validators": ["kramerius-links"],
                    "query": {"match_all": {}},
                },
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": "Validating records using 1 validators",
                "type": "ValidateRecords",
                "status": "Pending",
                "created_by": "12345678-1234-4678-9abc-1234567890ab",
                "created_at": "IGNORE",
                "started_at": None,
                "finished_at": None,
            },
            exclude_field_paths={("task_id",), ("created_at",)},
        )


@pytest_asyncio.fixture(scope="class")
async def catalog_record(
    db_session: DatabaseSession, indexer_session
) -> CatalogRecord:
    record = CatalogRecord(
        base="MZK01",
        system_number="VALIDATION-TEST",
        marc=load_test_record("MZK01-001217709.mrc")._marc,
    ).save(db_session)
    db_session.flush()
    await record.index(wait_for=True)
    return record


@pytest.fixture(scope="class")
def task(db_session: DatabaseSession, user: TokenData) -> Task:
    return Task(
        name="Validation test task",
        type=TaskType.ValidateRecords,
        created_by=user.user_id,
        data=ValidationTaskData(
            validators=["kramerius-links"],
            query={"query": {"match_all": {}}},
        ).model_dump(mode="json"),
    ).save(db_session)


@pytest.fixture(scope="class")
def mock_validator_result(class_mocker: MockerFixture) -> MockerFixture:
    class MockValidator(BaseValidator):
        async def run(self, record) -> ValidationResult:
            return ValidationResult(
                target=ValidationTarget(tag="001"),
                status=ValidityStatus.Valid,
                reason="Mock validation passed",
            )

    return class_mocker.patch(
        "validation.tasks.VALIDATOR_DISPATCHER",
        {"kramerius-links": MockValidator},
    )


@pytest.fixture(scope="class")
def mock_no_validator(class_mocker: MockerFixture) -> MockerFixture:
    return class_mocker.patch(
        "validation.tasks.VALIDATOR_DISPATCHER",
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
def validation(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
) -> Validation:
    return Validation(
        catalog_record_id=catalog_record.id,
        validator="kramerius-links",
        result={
            "target": {"tag": "001"},
            "status": "valid",
            "reason": "Mock validation passed",
        },
    ).save(db_session)


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "validation_settings",
    "task",
    "mock_validator_result",
)
class TestValidationTask:
    @pytest.mark.asyncio
    async def test_resulting_in_new_validation(
        self,
        db_session: DatabaseSession,
        task: Task,
    ):
        from validation.tasks import validate_records

        await validate_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "VALIDATION-TEST"
                ).validations
            )
            == 1
        )


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "validation_settings",
    "task",
    "mock_validator_result",
    "validation",
)
class TestValidationTaskWithExistingValidation:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        task: Task,
    ):
        from validation.tasks import validate_records

        await validate_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "VALIDATION-TEST"
                ).validations
            )
            == 1
        )


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "task",
    "mock_validator_result",
)
class TestValidationTaskNoSettingsFound:
    @pytest.mark.asyncio
    async def test_no_validator_settings_found(self, task: Task):
        from validation.tasks import validate_records

        with pytest.raises(ValueError, match="Validation settings not found"):
            await validate_records(task.task_id)


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "validation_settings",
    "task",
    "mock_no_validator",
)
class TestValidationTaskNoValidatorFound:
    @pytest.mark.asyncio
    async def test_no_validator_found(self, task: Task):
        from validation.tasks import validate_records

        with pytest.raises(
            ValueError, match="Unknown validator: kramerius-links"
        ):
            await validate_records(task.task_id)


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "validation_settings",
    "task",
    "mock_validator_result",
    "task_settings_one_by_one",
)
class TestValidationTaskIndexingOneByOne:
    @pytest.mark.asyncio
    async def test_indexing_one_by_one(self, task: Task):
        from validation.tasks import validate_records

        await validate_records(task.task_id)

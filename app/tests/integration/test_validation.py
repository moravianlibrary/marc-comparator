import pytest
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
from tests.conftest import (
    assert_response,
    create_catalog_record,
    load_test_json,
    load_test_record,
)
from validation.models import ValidationSettings, ValidationTaskData

# --- Fixtures ---


@pytest.fixture(scope="function")
def validation_settings(db_session: DatabaseSession) -> Settings:
    test_settings = load_test_json("validation_settings.json")
    return Settings.save(
        db_session,
        SettingsScope.Validation,
        ValidationSettings.model_validate(test_settings),
        ValidationSettings,
    )


@pytest.fixture(scope="function")
def catalog_record(
    db_session: DatabaseSession,
) -> CatalogRecord:
    return create_catalog_record(
        db_session,
        "MZK01",
        "000999002",
        load_test_record("MZK01-001217709.mrc"),
    )


@pytest.fixture(scope="function")
def task(db_session: DatabaseSession, user: TokenData) -> Task:
    return Task(
        name="Validation test task",
        type=TaskType.ValidateRecords,
        created_by=user.user_id,
        data=ValidationTaskData(
            validators=["kramerius-links"],
        ).model_dump(mode="json"),
    ).save(db_session)


@pytest.fixture(scope="function")
def mock_validator_result(mocker: MockerFixture) -> MockerFixture:
    class MockValidator(BaseValidator):
        async def run(self, record) -> list[ValidationResult]:
            return [
                ValidationResult(
                    target=ValidationTarget(tag="001"),
                    status=ValidityStatus.Valid,
                    reason="mock_passed",
                )
            ]

    return mocker.patch(
        "validation.tasks.VALIDATOR_DISPATCHER",
        {"kramerius-links": MockValidator},
    )


@pytest.fixture(scope="function")
def mock_no_validator(mocker: MockerFixture) -> MockerFixture:
    return mocker.patch(
        "validation.tasks.VALIDATOR_DISPATCHER",
        {},
    )


@pytest.fixture(scope="function")
def task_settings_one_by_one(db_session: DatabaseSession) -> TaskSettings:
    settings = TaskSettings(
        progress_update_interval=1,
        commit_interval=1,
    )
    return Settings.save(
        db_session,
        SettingsScope.Tasks,
        settings,
        TaskSettings,
    )


@pytest.fixture(scope="function")
def validation(
    db_session: DatabaseSession,
    catalog_record: CatalogRecord,
) -> Validation:
    validation = Validation(
        catalog_record_id=catalog_record.id,
        validator="kramerius-links",
        result={
            "target": {"tag": "001"},
            "status": "valid",
            "reason": "mock_passed",
        },
    )
    db_session.add(validation)
    db_session.commit()
    db_session.refresh(validation)
    return validation


# --- Test classes ---


class TestValidationEndpoints:
    @pytest.mark.asyncio
    async def test_validation_task_creation(
        self,
        db_session,
        user,
        tasks_client,
        validation_settings,
        client: AsyncClient,
    ):
        assert_response(
            await client.post(
                "/validation/task",
                json={
                    "validators": ["kramerius-links"],
                },
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": "Validating records using 1 validators",
                "type": "ValidateRecords",
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


class TestValidationTask:
    @pytest.mark.asyncio
    async def test_resulting_in_new_validation(
        self,
        db_session: DatabaseSession,
        tasks_client,
        catalog_record,
        validation_settings,
        task: Task,
        mock_validator_result,
    ):
        from validation.tasks import validate_records

        await validate_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "000999002"
                ).validations
            )
            == 1
        )


class TestValidationTaskWithExistingValidation:
    @pytest.mark.asyncio
    async def test_resulting_in_new_comparison(
        self,
        db_session: DatabaseSession,
        tasks_client,
        catalog_record,
        validation_settings,
        task: Task,
        mock_validator_result,
        validation,
    ):
        from validation.tasks import validate_records

        await validate_records(task.task_id)

        assert (
            len(
                CatalogRecord.find_by_base_and_system_number(
                    db_session, "MZK01", "000999002"
                ).validations
            )
            == 1
        )


class TestValidationTaskNoSettingsFound:
    @pytest.mark.asyncio
    async def test_no_validator_settings_found(
        self,
        db_session,
        tasks_client,
        catalog_record,
        task: Task,
        mock_validator_result,
    ):
        from validation.tasks import validate_records

        await validate_records(task.task_id)


class TestValidationTaskNoValidatorFound:
    @pytest.mark.asyncio
    async def test_no_validator_found(
        self,
        db_session,
        tasks_client,
        catalog_record,
        validation_settings,
        task: Task,
        mock_no_validator,
    ):
        from validation.tasks import validate_records

        await validate_records(task.task_id)


class TestValidationTaskIndexingOneByOne:
    @pytest.mark.asyncio
    async def test_indexing_one_by_one(
        self,
        db_session,
        tasks_client,
        catalog_record,
        validation_settings,
        task: Task,
        mock_validator_result,
        task_settings_one_by_one,
    ):
        from validation.tasks import validate_records

        await validate_records(task.task_id)

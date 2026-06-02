import pytest
from httpx import AsyncClient
from marc_comparator.authority_linkers import (
    AuthorityLink,
    BaseAuthorityLinker,
)
from pytest_mock import MockerFixture

from adapters.database import DatabaseSession
from auth.models import TokenData
from authority_linking.models import (
    AuthorityLinkingSettings,
    AuthorityLinkingTaskData,
)
from entities.authority_link import AuthorityLink as AuthorityLinkEntity
from entities.catalog_record import CatalogRecord
from entities.settings import Settings, SettingsScope
from entities.task import Task, TaskType
from tests.conftest import (
    assert_response,
    create_catalog_record,
    load_test_json,
    load_test_record,
)


class TestAuthorityLinkingEndpoints:
    @pytest.mark.asyncio
    async def test_authority_linking_task_creation(
        self,
        db_session: DatabaseSession,
        user,
        tasks_client,
        client: AsyncClient,
    ):
        test_settings = load_test_json("authority_linking_settings.json")

        Settings.save(
            db_session,
            SettingsScope.AuthorityLinking,
            AuthorityLinkingSettings.model_validate(test_settings),
            AuthorityLinkingSettings,
        )

        assert_response(
            await client.post(
                "/authority-linking/task",
                json={
                    "linkers": ["knihovny-cz"],
                    "target_base": "SKC",
                },
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": "Authority linking for base 'SKC'",
                "type": "LinkRecordsToAuthorities",
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


# --- Shared fixtures for task execution tests ---


@pytest.fixture(scope="function")
def catalog_record(
    db_session: DatabaseSession,
) -> CatalogRecord:
    return create_catalog_record(
        db_session,
        "MZK01",
        "001217709",
        load_test_record("MZK01-001217709.mrc"),
    )


@pytest.fixture(scope="function")
def authority_linking_settings(db_session: DatabaseSession) -> Settings:
    return Settings.save(
        db_session,
        SettingsScope.AuthorityLinking,
        AuthorityLinkingSettings.model_validate(load_test_json("authority_linking_settings.json")),
        AuthorityLinkingSettings,
    )


@pytest.fixture(scope="function")
def task(db_session: DatabaseSession, user: TokenData) -> Task:
    return Task(
        name="Authority linking for base 'SKC'",
        type=TaskType.LinkRecordsToAuthorities,
        created_by=user.user_id,
        data=AuthorityLinkingTaskData(
            linkers=["knihovny-cz"],
            target_base="SKC",
        ).model_dump(mode="json"),
    ).save(db_session)


@pytest.fixture(scope="function")
def authority_catalog_record(db_session: DatabaseSession) -> CatalogRecord:
    return create_catalog_record(
        db_session,
        "SKC",
        "001217729",
        load_test_record("MZK01-001217729.mrc"),
    )


@pytest.fixture(scope="function")
def authority_link(db_session: DatabaseSession) -> AuthorityLinkEntity:
    main_record_id = CatalogRecord.generate_id("MZK01", "001217709")
    authority_record_id = CatalogRecord.generate_id("SKC", "001217729")

    AuthorityLinkEntity(
        main_record_id=main_record_id,
        linker="knihovny-cz",
        base="SKC",
        authority_record_id=authority_record_id,
        confidence=0.5,
    ).save(db_session)


@pytest.fixture(scope="function")
def mock_linker_with_link(mocker: MockerFixture) -> MockerFixture:
    class MockLinker(BaseAuthorityLinker):
        async def get_target_bases(self, config):
            return ["SKC"]

        async def run(self, base, system_number, record, target_base):
            return AuthorityLink(base=target_base, system_number="001217729", record=record)

    return mocker.patch(
        "authority_linking.tasks.AUTHORITY_LINKER_DISPATCHER",
        {"knihovny-cz": MockLinker},
    )


@pytest.fixture(scope="function")
def mock_linker_with_no_link(mocker: MockerFixture) -> MockerFixture:
    class MockLinker(BaseAuthorityLinker):
        async def get_target_bases(self, config):
            return ["SKC"]

        async def run(self, base, system_number, record, target_base):
            return None

    return mocker.patch(
        "authority_linking.tasks.AUTHORITY_LINKER_DISPATCHER",
        {"knihovny-cz": MockLinker},
    )


@pytest.fixture(scope="function")
def mock_no_linker(mocker: MockerFixture) -> MockerFixture:
    return mocker.patch(
        "authority_linking.tasks.AUTHORITY_LINKER_DISPATCHER",
        {"knihovny-cz": None},
    )


# --- Task execution test classes ---


class TestAuthorityLinkingTask:
    @pytest.mark.asyncio
    async def test_new_link_found(
        self,
        db_session: DatabaseSession,
        tasks_client,
        catalog_record,
        authority_linking_settings,
        task: Task,
        mock_linker_with_link: MockerFixture,
    ):
        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

        assert (
            CatalogRecord.find_by_base_and_system_number(db_session, "SKC", "001217729") is not None
        )

    @pytest.mark.asyncio
    async def test_no_link_found(
        self,
        db_session,
        tasks_client,
        catalog_record,
        authority_linking_settings,
        task: Task,
        mock_linker_with_no_link: MockerFixture,
    ):
        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

    @pytest.mark.asyncio
    async def test_no_linker_found(
        self,
        db_session,
        tasks_client,
        catalog_record,
        authority_linking_settings,
        task: Task,
        mock_no_linker: MockerFixture,
    ):
        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)


class TestAuthorityLinkingTaskExistingRecord:
    @pytest.mark.asyncio
    async def test_new_link_found_with_existing_record(
        self,
        db_session: DatabaseSession,
        tasks_client,
        catalog_record,
        authority_linking_settings,
        task: Task,
        authority_catalog_record: CatalogRecord,
        mock_linker_with_link: MockerFixture,
    ):
        latest_sync = authority_catalog_record.latest_sync

        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

        assert (
            latest_sync
            != CatalogRecord.find_by_base_and_system_number(
                db_session, "SKC", "001217729"
            ).latest_sync
        )


class TestAuthorityLinkingTaskExistingRecordExistingLink:
    @pytest.mark.asyncio
    async def test_existing_link_found_with_existing_record(
        self,
        db_session: DatabaseSession,
        tasks_client,
        catalog_record,
        authority_linking_settings,
        task: Task,
        authority_catalog_record: CatalogRecord,
        authority_link,
        mock_linker_with_link: MockerFixture,
    ):
        latest_sync = authority_catalog_record.latest_sync

        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

        assert (
            latest_sync
            != CatalogRecord.find_by_base_and_system_number(
                db_session, "SKC", "001217729"
            ).latest_sync
        )


class TestAuthorityLinkingTaskNoLinkerSettings:
    @pytest.mark.asyncio
    async def test_no_linker_settings_found(
        self,
        db_session,
        tasks_client,
        catalog_record,
        task: Task,
        mock_linker_with_no_link: MockerFixture,
    ):
        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

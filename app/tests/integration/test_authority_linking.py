import pytest
import pytest_asyncio
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
from tests.integration.conftest import (
    assert_response,
    load_test_json,
    load_test_record,
)


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "client",
    "user",
    "tasks_client",
)
class TestAuthorityLinkingEndpoints:
    @pytest.mark.asyncio
    async def test_authority_linking_task_creation(
        self, db_session: DatabaseSession, client: AsyncClient
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
                    "query": {"match_all": {}},
                },
            ),
            200,
            {
                "task_id": "IGNORE",
                "name": "Authority linking for base 'SKC'",
                "type": "LinkRecordsToAuthorities",
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
        system_number="001217709",
        marc=load_test_record("MZK01-001217709.mrc")._marc,
    ).save(db_session)
    await record.index(wait_for=True)


@pytest.fixture(scope="class")
def authority_linking_settings(
    db_session: DatabaseSession,
) -> Settings:
    return Settings.save(
        db_session,
        SettingsScope.AuthorityLinking,
        AuthorityLinkingSettings.model_validate(
            load_test_json("authority_linking_settings.json")
        ),
        AuthorityLinkingSettings,
    )


@pytest.fixture(scope="class")
def task(db_session: DatabaseSession, user: TokenData) -> Task:
    return Task(
        name="Authority linking for base 'SKC'",
        type=TaskType.LinkRecordsToAuthorities,
        created_by=user.user_id,
        data=AuthorityLinkingTaskData(
            linkers=["knihovny-cz"],
            target_base="SKC",
            query={"query": {"match_all": {}}},
        ).model_dump(mode="json"),
    ).save(db_session)


@pytest.fixture(scope="class")
def authority_catalog_record(
    db_session: DatabaseSession,
) -> CatalogRecord:
    return CatalogRecord(
        base="SKC",
        system_number="001217729",
        marc=load_test_record("MZK01-001217729.mrc")._marc,
    ).save(db_session)


@pytest.fixture(scope="class")
def authority_link(
    db_session: DatabaseSession,
) -> AuthorityLinkEntity:
    main_record_id = CatalogRecord.generate_id("MZK01", "001217709")
    authority_record_id = CatalogRecord.generate_id("SKC", "001217729")

    AuthorityLinkEntity(
        main_record_id=main_record_id,
        authority_record_id=authority_record_id,
        confidence=0.5,
    ).save(db_session)


@pytest.fixture(scope="function")
def mock_linker_with_link(mocker: MockerFixture) -> MockerFixture:
    class MockLinker(BaseAuthorityLinker):
        async def run(self, base, system_number, record, target_base):
            return AuthorityLink(
                base=target_base, system_number="001217729", record=record
            )

    return mocker.patch(
        "authority_linking.tasks.AUTHORITY_LINKER_DISPATCHER",
        {"knihovny-cz": MockLinker},
    )


@pytest.fixture(scope="function")
def mock_linker_with_no_link(mocker: MockerFixture) -> MockerFixture:
    class MockLinker(BaseAuthorityLinker):
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


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "authority_linking_settings",
    "task",
)
class TestAuthorityLinkingTask:
    @pytest.mark.asyncio
    async def test_new_link_found(
        self,
        db_session: DatabaseSession,
        task: Task,
        mock_linker_with_link: MockerFixture,
    ):
        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

        assert (
            CatalogRecord.find_by_base_and_system_number(
                db_session, "SKC", "001217729"
            )
            is not None
        )

    @pytest.mark.asyncio
    async def test_no_link_found(
        self, task: Task, mock_linker_with_no_link: MockerFixture
    ):
        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

    @pytest.mark.asyncio
    async def test_no_linker_found(
        self, task: Task, mock_no_linker: MockerFixture
    ):
        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "authority_linking_settings",
    "task",
    "authority_catalog_record",
)
class TestAuthorityLinkingTaskExistingRecord:
    @pytest.mark.asyncio
    async def test_new_link_found_with_existing_record(
        self,
        db_session: DatabaseSession,
        task: Task,
        authority_catalog_record: CatalogRecord,
        mock_linker_with_link: MockerFixture,
    ):
        last_sync = authority_catalog_record.last_sync

        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

        assert (
            last_sync
            != CatalogRecord.find_by_base_and_system_number(
                db_session, "SKC", "001217729"
            ).last_sync
        )


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "authority_linking_settings",
    "task",
    "authority_catalog_record",
    "authority_link",
)
class TestAuthorityLinkingTaskExistingRecordExistingLink:
    @pytest.mark.asyncio
    async def test_existing_link_found_with_existing_record(
        self,
        db_session: DatabaseSession,
        task: Task,
        authority_catalog_record: CatalogRecord,
        mock_linker_with_link: MockerFixture,
    ):
        last_sync = authority_catalog_record.last_sync

        from authority_linking.tasks import authority_linking

        await authority_linking(task.task_id)

        assert (
            last_sync
            != CatalogRecord.find_by_base_and_system_number(
                db_session, "SKC", "001217729"
            ).last_sync
        )


@pytest.mark.usefixtures(
    "tasks_client",
    "catalog_record",
    "task",
)
class TestAuthorityLinkingTaskNoLinkerSettings:
    @pytest.mark.asyncio
    async def test_no_linker_settings_found(
        self, task: Task, mock_linker_with_no_link: MockerFixture
    ):
        from authority_linking.tasks import authority_linking

        with pytest.raises(
            ValueError, match="Authority linking settings not found"
        ):
            await authority_linking(task.task_id)

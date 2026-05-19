import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from auth.models import TokenData
from entities.task import Task, TaskStatus, TaskType
from entities.user import User
from entities.role import Role
from tests.conftest import FAKE_USER_ID, assert_response


@pytest.fixture
def task_with_traceback(
    db_session: DatabaseSession, user: TokenData
) -> Task:
    task = Task(
        name="Task with traceback",
        type=TaskType.FetchRecord,
        created_by=user.user_id,
        traceback="line0\nline1\nline2\nline3\nline4\n",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def pending_task(db_session: DatabaseSession, user: TokenData) -> Task:
    task = Task(
        name="Pending task",
        type=TaskType.FetchRecord,
        created_by=user.user_id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def completed_task(db_session: DatabaseSession, user: TokenData) -> Task:
    task = Task(
        name="Completed task",
        type=TaskType.FetchRecord,
        status=TaskStatus.Success,
        created_by=user.user_id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def guest_user(db_session: DatabaseSession) -> User:
    """A non-admin user with ManageTasks but not ManageAllTasks."""
    from entities.role import Permission

    limited_role = Role(
        name="LimitedTaskManager",
        permissions=[Permission.ReadRecords, Permission.ManageTasks],
    )
    limited_role.save(db_session)

    guest = User(
        first_name="Guest",
        last_name="User",
        email="guest@example.com",
        password_hash="guestpasswordhash",
    )
    guest.save(db_session)
    guest.roles.append(limited_role)
    db_session.commit()
    return guest


class TestTracebackLines:
    @pytest.mark.asyncio
    async def test_get_traceback_full(
        self,
        db_session,
        indexer_session,
        user,
        client: AsyncClient,
        task_with_traceback: Task,
    ):
        response = await client.get(
            f"/tasks/{task_with_traceback.task_id}/traceback"
        )
        assert response.status_code == 200
        lines = response.text.split("\n")
        assert len(lines) == 5  # "line0" through "line4"

    @pytest.mark.asyncio
    async def test_get_traceback_with_range(
        self,
        db_session,
        indexer_session,
        user,
        client: AsyncClient,
        task_with_traceback: Task,
    ):
        response = await client.get(
            f"/tasks/{task_with_traceback.task_id}/traceback",
            params={"from": 1, "to": 3},
        )
        assert response.status_code == 200
        lines = response.text.split("\n")
        assert lines == ["line1", "line2"]

    @pytest.mark.asyncio
    async def test_get_traceback_empty_task(
        self,
        db_session,
        indexer_session,
        user,
        client: AsyncClient,
        pending_task: Task,
    ):
        response = await client.get(
            f"/tasks/{pending_task.task_id}/traceback"
        )
        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.asyncio
    async def test_get_traceback_permission_denied(
        self,
        db_session,
        indexer_session,
        user,
        client: AsyncClient,
        guest_user: User,
        task_with_traceback: Task,
    ):
        """Guest user (without ManageAllTasks) cannot access other user's traceback."""
        from app import app
        from auth.service import get_current_user

        guest_token = TokenData(user_id=str(guest_user.id))
        app.dependency_overrides[get_current_user] = lambda: guest_token

        try:
            assert_response(
                await client.get(
                    f"/tasks/{task_with_traceback.task_id}/traceback"
                ),
                403,
                {
                    "detail": "You do not have permission to access this task."
                },
            )
        finally:
            # Restore admin user override
            admin_token = TokenData(user_id=FAKE_USER_ID)
            app.dependency_overrides[get_current_user] = lambda: admin_token


class TestRevokeTask:
    @pytest.mark.asyncio
    async def test_revoke_pending_task(
        self,
        db_session,
        indexer_session,
        user,
        tasks_client,
        client: AsyncClient,
        pending_task: Task,
    ):
        response = await client.patch(
            f"/tasks/{pending_task.task_id}/revoke"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "Revoked"

    @pytest.mark.asyncio
    async def test_revoke_completed_task_fails(
        self,
        db_session,
        indexer_session,
        user,
        tasks_client,
        client: AsyncClient,
        completed_task: Task,
    ):
        assert_response(
            await client.patch(
                f"/tasks/{completed_task.task_id}/revoke"
            ),
            400,
            {"detail": "Task with status 'Success' cannot be revoked."},
        )

    @pytest.mark.asyncio
    async def test_revoke_permission_denied(
        self,
        db_session,
        indexer_session,
        user,
        tasks_client,
        client: AsyncClient,
        guest_user: User,
        pending_task: Task,
    ):
        """Guest user cannot revoke another user's task."""
        from app import app
        from auth.service import get_current_user

        guest_token = TokenData(user_id=str(guest_user.id))
        app.dependency_overrides[get_current_user] = lambda: guest_token

        try:
            assert_response(
                await client.patch(
                    f"/tasks/{pending_task.task_id}/revoke"
                ),
                403,
                {
                    "detail": "You do not have permission to revoke this task."
                },
            )
        finally:
            admin_token = TokenData(user_id=FAKE_USER_ID)
            app.dependency_overrides[get_current_user] = lambda: admin_token


class TestDeleteTasks:
    @pytest.mark.asyncio
    async def test_delete_tasks_enqueue(
        self,
        db_session,
        indexer_session,
        user,
        tasks_client,
        client: AsyncClient,
    ):
        response = await client.post(
            "/tasks/delete",
            json={"query": {"match_all": {}}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Deleting tasks"
        assert body["type"] == "DeleteTasks"
        assert body["status"] == "Pending"

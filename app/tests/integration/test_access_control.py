from typing import Generator, Tuple

import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from entities.role import Role
from entities.user import User
from tests.integration.conftest import assert_response


@pytest.fixture(scope="class")
def test_users(
    db_session: DatabaseSession,
) -> Generator[Tuple[User, User], None, None]:

    # Create test roles
    Role.create_default_roles(db_session)

    # Create test users
    user1 = User(
        email="user1@example.com",
        first_name="User",
        last_name="One",
        password_hash="password1",
    )
    user1.save(db_session)

    user1.roles.append(Role.get_by_name(db_session, "Guest"))
    user1.save(db_session)

    user2 = User(
        email="user2@example.com",
        first_name="User",
        last_name="Two",
        password_hash="password2",
    )
    user2.save(db_session)

    yield [user1, user2]

    user1.delete(db_session)
    user2.delete(db_session)


@pytest.mark.usefixtures(
    "db_session",
    "indexer_session",
    "client",
    "user",
    "tasks_client",
    "test_users",
)
class TestAccessControlEndpoints:
    @pytest.mark.asyncio
    async def test_get_roles(self, client: AsyncClient):
        assert_response(
            await client.get("/access-control/roles"),
            200,
            {
                "items": [
                    {
                        "id": 1,
                        "name": "Admin",
                        "permissions": [
                            "ReadRecords",
                            "AddRecords",
                            "SyncRecordsFromCatalog",
                            "RunRecordTasks",
                            "ManageTasks",
                            "ManageAllTasks",
                            "ManageAccessControl",
                            "ManageAppSettings",
                            "ManageTaskSettings",
                            "ManageSystem",
                        ],
                        "immutable": True,
                        "protected": True,
                    },
                    {
                        "id": 2,
                        "name": "Guest",
                        "permissions": ["ReadRecords"],
                        "immutable": False,
                        "protected": True,
                    },
                ],
                "num_found": 2,
            },
        )

    @pytest.mark.asyncio
    async def test_create_role(
        self, db_session: DatabaseSession, client: AsyncClient
    ):
        from entities.role import Role

        Role.create_default_roles(db_session)

        new_role_data = {
            "name": "TestRole",
            "permissions": ["ReadRecords", "AddRecords"],
        }

        assert_response(
            await client.post("/access-control/roles", json=new_role_data),
            200,
            {
                "id": 3,
                "name": "TestRole",
                "permissions": ["ReadRecords", "AddRecords"],
                "immutable": False,
                "protected": False,
            },
        )

    @pytest.mark.asyncio
    async def test_update_role(self, client: AsyncClient):
        update_role_data = {
            "name": "Guest",
            "permissions": ["ReadRecords", "AddRecords"],
        }

        assert_response(
            await client.put("/access-control/roles/2", json=update_role_data),
            200,
            {
                "id": 2,
                "name": "Guest",
                "permissions": ["ReadRecords", "AddRecords"],
                "immutable": False,
                "protected": True,
            },
        )

    @pytest.mark.asyncio
    async def test_update_immutable_role_fails(self, client: AsyncClient):
        assert_response(
            await client.put(
                "/access-control/roles/1",
                json={
                    "name": "Admin",
                    "permissions": ["ReadRecords"],
                },
            ),
            400,
            {"detail": "Cannot modify an immutable role"},
        )

    @pytest.mark.asyncio
    async def test_update_protected_role_fails(self, client: AsyncClient):
        assert_response(
            await client.put(
                "/access-control/roles/2",
                json={
                    "name": "AdminUpdated",
                    "permissions": ["ReadRecords"],
                },
            ),
            400,
            {"detail": "Cannot rename a protected role"},
        )

    @pytest.mark.asyncio
    async def test_delete_role(
        self, db_session: DatabaseSession, client: AsyncClient
    ):
        from entities.role import Role

        Role.create_default_roles(db_session)

        # First, create a new role to delete
        new_role = Role(name="DeletableRole", permissions=[])
        new_role.save(db_session)

        assert_response(
            await client.delete(f"/access-control/roles/{new_role.id}"),
            200,
            {
                "id": new_role.id,
                "name": "DeletableRole",
                "permissions": [],
                "immutable": False,
                "protected": False,
            },
        )

    @pytest.mark.asyncio
    async def test_delete_immutable_role_fails(self, client: AsyncClient):
        assert_response(
            await client.delete("/access-control/roles/1"),
            400,
            {"detail": "Cannot delete an immutable role"},
        )

    @pytest.mark.asyncio
    async def test_delete_protected_role_fails(self, client: AsyncClient):
        assert_response(
            await client.delete("/access-control/roles/2"),
            400,
            {"detail": "Cannot delete a protected role"},
        )

    @pytest.mark.asyncio
    async def test_get_users(self, test_users, client: AsyncClient):
        user1, user2 = test_users
        assert_response(
            await client.get("/access-control/users"),
            200,
            {
                "items": [
                    {
                        "id": "12345678-1234-4678-9abc-1234567890ab",
                        "email": "admin@example.com",
                        "first_name": "Admin",
                        "last_name": "User",
                        "roles": [
                            {"id": 1, "name": "Admin"},
                        ],
                    },
                    {
                        "id": str(user1.id),
                        "email": "user1@example.com",
                        "first_name": "User",
                        "last_name": "One",
                        "roles": [
                            {"id": 2, "name": "Guest"},
                        ],
                    },
                    {
                        "id": str(user2.id),
                        "email": "user2@example.com",
                        "first_name": "User",
                        "last_name": "Two",
                        "roles": [],
                    },
                ],
                "num_found": 3,
            },
        )

    @pytest.mark.asyncio
    async def test_get_users_with_email_filter(
        self, test_users, client: AsyncClient
    ):
        user1, _ = test_users
        assert_response(
            await client.get(
                "/access-control/users", params={"email": "user1"}
            ),
            200,
            {
                "items": [
                    {
                        "id": str(user1.id),
                        "email": "user1@example.com",
                        "first_name": "User",
                        "last_name": "One",
                        "roles": [
                            {"id": 2, "name": "Guest"},
                        ],
                    },
                ],
                "num_found": 1,
            },
        )

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, test_users, client: AsyncClient):
        user, _ = test_users
        assert_response(
            await client.patch(
                f"/access-control/users/{user.id}/assign-role/1"
            ),
            200,
            {
                "id": str(user.id),
                "email": "user1@example.com",
                "first_name": "User",
                "last_name": "One",
                "roles": [
                    {"id": 1, "name": "Admin"},
                    {"id": 2, "name": "Guest"},
                ],
            },
        )

import pytest
from httpx import AsyncClient

from adapters.database import DatabaseSession
from entities.role import Role
from entities.user import User
from tests.conftest import assert_response


@pytest.fixture(scope="function")
def test_users(db_session: DatabaseSession):
    Role.create_default_roles(db_session)

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

    return [user1, user2]


class TestAccessControlEndpoints:
    @pytest.mark.asyncio
    async def test_get_roles(
        self, db_session, user, client: AsyncClient, test_users
    ):
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
        self, db_session: DatabaseSession, user, client: AsyncClient
    ):
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
    async def test_update_role(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

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
    async def test_update_immutable_role_fails(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

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
    async def test_update_protected_role_fails(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

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
        self, db_session: DatabaseSession, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

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
    async def test_delete_immutable_role_fails(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

        assert_response(
            await client.delete("/access-control/roles/1"),
            400,
            {"detail": "Cannot delete an immutable role"},
        )

    @pytest.mark.asyncio
    async def test_delete_protected_role_fails(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

        assert_response(
            await client.delete("/access-control/roles/2"),
            400,
            {"detail": "Cannot delete a protected role"},
        )

    @pytest.mark.asyncio
    async def test_get_users(
        self, db_session, user, client: AsyncClient, test_users
    ):
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
        self, db_session, user, client: AsyncClient, test_users
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
    async def test_assign_role_to_user(
        self, db_session, user, client: AsyncClient, test_users
    ):
        user1, _ = test_users
        assert_response(
            await client.patch(
                f"/access-control/users/{user1.id}/assign-role/1"
            ),
            200,
            {
                "id": str(user1.id),
                "email": "user1@example.com",
                "first_name": "User",
                "last_name": "One",
                "roles": [
                    {"id": 1, "name": "Admin"},
                    {"id": 2, "name": "Guest"},
                ],
            },
        )

    @pytest.mark.asyncio
    async def test_unassign_role_from_user(
        self, db_session, user, client: AsyncClient, test_users
    ):
        user1, _ = test_users
        # user1 has Guest role assigned; unassign it
        assert_response(
            await client.patch(
                f"/access-control/users/{user1.id}/unassign-role/2"
            ),
            200,
            {
                "id": str(user1.id),
                "email": "user1@example.com",
                "first_name": "User",
                "last_name": "One",
                "roles": [],
            },
        )

    @pytest.mark.asyncio
    async def test_unassign_role_not_assigned(
        self, db_session, user, client: AsyncClient, test_users
    ):
        """Unassigning a role the user doesn't have should succeed (no-op)."""
        _, user2 = test_users
        # user2 has no roles; unassigning Admin should be a no-op
        assert_response(
            await client.patch(
                f"/access-control/users/{user2.id}/unassign-role/1"
            ),
            200,
            {
                "id": str(user2.id),
                "email": "user2@example.com",
                "first_name": "User",
                "last_name": "Two",
                "roles": [],
            },
        )

    @pytest.mark.asyncio
    async def test_get_roles_pagination(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

        # page_size=1 should return only the first role
        assert_response(
            await client.get(
                "/access-control/roles",
                params={"page": 1, "page_size": 1},
            ),
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
                ],
                "num_found": 2,
            },
        )

        # page 2 should return the second role
        assert_response(
            await client.get(
                "/access-control/roles",
                params={"page": 2, "page_size": 1},
            ),
            200,
            {
                "items": [
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
    async def test_get_roles_empty_page(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

        # page 100 should return empty items
        assert_response(
            await client.get(
                "/access-control/roles",
                params={"page": 100, "page_size": 10},
            ),
            200,
            {"items": [], "num_found": 2},
        )

    @pytest.mark.asyncio
    async def test_get_users_pagination(
        self, db_session, user, client: AsyncClient, test_users
    ):
        # 3 users total (admin + user1 + user2), page_size=1
        assert_response(
            await client.get(
                "/access-control/users",
                params={"page": 1, "page_size": 1},
            ),
            200,
            {"num_found": 3},
            {("items",)},
        )

    @pytest.mark.asyncio
    async def test_get_users_email_filter_no_match(
        self, db_session, user, client: AsyncClient, test_users
    ):
        assert_response(
            await client.get(
                "/access-control/users",
                params={"email": "nonexistent"},
            ),
            200,
            {"items": [], "num_found": 0},
        )

    @pytest.mark.asyncio
    async def test_create_role_with_all_permissions(
        self, db_session, user, client: AsyncClient
    ):
        Role.create_default_roles(db_session)

        all_permissions = [
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
        ]
        assert_response(
            await client.post(
                "/access-control/roles",
                json={"name": "SuperRole", "permissions": all_permissions},
            ),
            200,
            {
                "id": 3,
                "name": "SuperRole",
                "permissions": all_permissions,
                "immutable": False,
                "protected": False,
            },
        )

    @pytest.mark.asyncio
    async def test_update_role_permissions_only(
        self, db_session, user, client: AsyncClient
    ):
        """Updating a protected role's permissions (without renaming) should succeed."""
        Role.create_default_roles(db_session)

        assert_response(
            await client.put(
                "/access-control/roles/2",
                json={
                    "name": "Guest",
                    "permissions": [
                        "ReadRecords",
                        "AddRecords",
                        "SyncRecordsFromCatalog",
                    ],
                },
            ),
            200,
            {
                "id": 2,
                "name": "Guest",
                "permissions": [
                    "ReadRecords",
                    "AddRecords",
                    "SyncRecordsFromCatalog",
                ],
                "immutable": False,
                "protected": True,
            },
        )

import { ReactElement, useState } from "react";
import {
    InnerScrollContainer,
    OuterScrollContainer,
    Table,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
} from "@patternfly/react-table";
import {
    Dropdown,
    DropdownItem,
    MenuToggle,
    Pagination,
    SearchInput,
    Toolbar,
    ToolbarContent,
    ToolbarItem,
} from "@patternfly/react-core";
import {
    useAssignUserRole,
    useGetUsers,
    useUnassignUserRole,
} from "../hooks/useUsers";
import { useGetRoles } from "../hooks/useRoles";
import { type User, type UserId } from "../models/api/responses/users";
import SelectUserRoles from "./user-management/SelectUserRoles";

const UserManagement = (): ReactElement => {
    const [page, setPage] = useState<number>(1);
    const [pageSize, setPageSize] = useState<number>(10);
    const [searchTermBuffer, setSearchTermBuffer] = useState<string>("");
    const [searchTerm, setSearchTerm] = useState<string | null>(null);
    const [openDropdownUserId, setOpenDropdownUserId] = useState<string | null>(
        null
    );

    const { data: usersPage } = useGetUsers({
        page,
        page_size: pageSize,
        email: searchTerm,
    });
    const { data: rolesData } = useGetRoles({ page: 1, page_size: 1000 });
    const assignUserRoleMutation = useAssignUserRole();
    const unassignUserRoleMutation = useUnassignUserRole();

    const handlePaginationChange = (newPage: number, newPerPage?: number) => {
        setPage(newPage);
        if (newPerPage) {
            setPageSize(newPerPage);
        }
    };

    const handleAssignRole = (userId: UserId, roleId: number) => {
        assignUserRoleMutation.mutate({ user_id: userId, role_id: roleId });
    };

    const handleUnassignRole = (userId: UserId, roleId: number) => {
        unassignUserRoleMutation.mutate({ user_id: userId, role_id: roleId });
    };

    return (
        <OuterScrollContainer
            style={{
                marginLeft: 20,
                marginRight: 20,
                marginTop: 10,
                marginBottom: 10,
            }}
        >
            <Toolbar>
                <ToolbarContent>
                    <ToolbarItem align={{ default: "alignStart" }}>
                        <SearchInput
                            placeholder="Search users by email"
                            value={searchTermBuffer}
                            onChange={(_event, value) =>
                                setSearchTermBuffer(value)
                            }
                            onClear={() => {
                                setSearchTermBuffer("");
                                setSearchTerm(null);
                            }}
                            onSearch={() =>
                                setSearchTerm(searchTermBuffer.trim() || null)
                            }
                        />
                    </ToolbarItem>
                    <ToolbarItem align={{ default: "alignEnd" }}>
                        <Pagination
                            perPageOptions={[
                                { title: "10", value: 10 },
                                { title: "20", value: 20 },
                                { title: "50", value: 50 },
                            ]}
                            itemCount={usersPage?.num_found || 0}
                            perPage={pageSize}
                            page={page}
                            onSetPage={(_event, newPage, newPerPage) =>
                                handlePaginationChange(newPage, newPerPage)
                            }
                            onPerPageSelect={(_event, newPerPage, newPage) =>
                                handlePaginationChange(newPage, newPerPage)
                            }
                        />
                    </ToolbarItem>
                </ToolbarContent>
            </Toolbar>
            <InnerScrollContainer>
                <Table isStickyHeader>
                    <Thead>
                        <Tr>
                            <Th>ID</Th>
                            <Th>Email</Th>
                            <Th>First Name</Th>
                            <Th>Last Name</Th>
                            <Th>Roles</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {usersPage?.items.map((user) => (
                            <Tr key={user.id}>
                                <Td>{user.id}</Td>
                                <Td>{user.email}</Td>
                                <Td>{user.first_name}</Td>
                                <Td>{user.last_name}</Td>
                                <Td>
                                    <SelectUserRoles
                                        userRoles={user.roles}
                                        allRoles={rolesData?.items || []}
                                        onAssignRole={(roleId: number) =>
                                            handleAssignRole(user.id, roleId)
                                        }
                                        onUnassignRole={(roleId: number) =>
                                            handleUnassignRole(user.id, roleId)
                                        }
                                    />
                                </Td>
                            </Tr>
                        ))}
                    </Tbody>
                </Table>
            </InnerScrollContainer>
        </OuterScrollContainer>
    );
};

export default UserManagement;

import { type ReactElement, useState } from "react";
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
    useCreateRole,
    useDeleteRole,
    useGetRoles,
    useUpdateRole,
} from "../hooks/useRoles";
import {
    ActionList,
    ActionListGroup,
    ActionListItem,
    Button,
    Content,
    Label,
    LabelGroup,
    Modal,
    ModalBody,
    ModalFooter,
    ModalHeader,
    ModalVariant,
    PageGroup,
    PageSection,
    Pagination,
    Toolbar,
    ToolbarContent,
    ToolbarItem,
} from "@patternfly/react-core";
import { PencilAltIcon, TrashIcon } from "@patternfly/react-icons";
import EditRoleForm from "../components/roles/organisms/EditRoleForm";
import { type RoleResponse } from "../models/api/responses/roles";
import { type EditRole } from "../models/api/requests/roles";
import { useTranslation } from "react-i18next";

const RoleManagement = (): ReactElement => {
    const { t } = useTranslation("roles");

    const [page, setPage] = useState<number>(1);
    const [pageSize, setPageSize] = useState<number>(10);
    const [editRole, setEditRole] = useState<Partial<RoleResponse> | null>(
        null
    );
    const [deleteRole, setDeleteRole] = useState<RoleResponse | null>(null);

    const { data: rolesPage } = useGetRoles({ page, page_size: pageSize });
    const createRoleMutation = useCreateRole();
    const updateRoleMutation = useUpdateRole();
    const deleteRoleMutation = useDeleteRole();

    const handlePaginationChange = (newPage: number, newPerPage?: number) => {
        setPage(newPage);
        if (newPerPage) {
            setPageSize(newPerPage);
        }
    };

    const handleEditRoleSubmit = (data: EditRole) => {
        if (editRole?.id) {
            updateRoleMutation.mutate({ id: editRole.id, data });
        } else {
            createRoleMutation.mutate(data);
        }
        setEditRole(null);
    };

    const handleDeleteRole = (roleId: number) => {
        deleteRoleMutation.mutate({ id: roleId });
    };

    return (
        <OuterScrollContainer>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>{t("role-management-title")}</h1>
                    </Content>
                </PageSection>
            </PageGroup>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Toolbar>
                        <ToolbarContent rowWrap={{ default: "nowrap" }}>
                            <ToolbarItem align={{ default: "alignStart" }}>
                                <Button
                                    variant="primary"
                                    onClick={() =>
                                        setEditRole({
                                            name: "",
                                            permissions: [],
                                        })
                                    }
                                >
                                    {t("create-role-button")}
                                </Button>
                            </ToolbarItem>
                            {(rolesPage?.num_found || 0) > 10 && (
                                <ToolbarItem align={{ default: "alignEnd" }}>
                                    <Pagination
                                        perPageOptions={[
                                            { title: "10", value: 10 },
                                            { title: "20", value: 20 },
                                            { title: "50", value: 50 },
                                        ]}
                                        itemCount={rolesPage?.num_found || 0}
                                        perPage={pageSize}
                                        page={page}
                                        onSetPage={(
                                            _event,
                                            newPage,
                                            newPerPage
                                        ) =>
                                            handlePaginationChange(
                                                newPage,
                                                newPerPage
                                            )
                                        }
                                        onPerPageSelect={(
                                            _event,
                                            newPerPage,
                                            newPage
                                        ) =>
                                            handlePaginationChange(
                                                newPage,
                                                newPerPage
                                            )
                                        }
                                        titles={{
                                            perPageSuffix: t(
                                                "pagination.per-page-suffix"
                                            ),
                                            ofWord: t("pagination.of"),
                                        }}
                                    />
                                </ToolbarItem>
                            )}
                        </ToolbarContent>
                    </Toolbar>
                </PageSection>
            </PageGroup>
            <InnerScrollContainer
                style={{
                    marginLeft: 20,
                    marginRight: 20,
                    marginTop: 10,
                    marginBottom: 10,
                }}
            >
                <Table isStickyHeader>
                    <Thead>
                        <Tr>
                            <Th>{t("fields.name")}</Th>
                            <Th>{t("fields.permissions")}</Th>
                            <Th>{t("fields.actions")}</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {rolesPage?.items.map((role) => (
                            <Tr key={role.id}>
                                <Td>{role.name}</Td>
                                <Td>
                                    <LabelGroup numLabels={10}>
                                        {role.permissions.map((permission) => (
                                            <Label
                                                key={permission}
                                                variant="outline"
                                            >
                                                {t(`permissions.${permission}`)}
                                            </Label>
                                        ))}
                                    </LabelGroup>
                                </Td>
                                <Td>
                                    <ActionList>
                                        <ActionListGroup>
                                            <ActionListItem>
                                                <Button
                                                    variant="secondary"
                                                    icon={<PencilAltIcon />}
                                                    isDisabled={role.immutable}
                                                    onClick={() =>
                                                        setEditRole(role)
                                                    }
                                                />
                                            </ActionListItem>
                                            <ActionListItem>
                                                <Button
                                                    variant="secondary"
                                                    isDanger
                                                    icon={<TrashIcon />}
                                                    isDisabled={
                                                        role.immutable ||
                                                        role.protected
                                                    }
                                                    onClick={() =>
                                                        setDeleteRole(role)
                                                    }
                                                />
                                            </ActionListItem>
                                        </ActionListGroup>
                                    </ActionList>
                                </Td>
                            </Tr>
                        ))}
                    </Tbody>
                </Table>
            </InnerScrollContainer>
            <Modal
                variant={ModalVariant.small}
                isOpen={editRole !== null}
                onClose={() => setEditRole(null)}
                onEscapePress={() => setEditRole(null)}
                aria-labelledby="modal-with-dropdown"
                aria-describedby="modal-box-body-with-dropdown"
            >
                <ModalHeader
                    title={
                        editRole?.id
                            ? t("edit-role-title")
                            : t("create-role-title")
                    }
                    labelId="modal-with-dropdown"
                />
                <ModalBody id="modal-box-body-with-dropdown">
                    <EditRoleForm
                        initialData={{
                            name: editRole?.name || "",
                            permissions: editRole?.permissions || [],
                        }}
                        isNewRole={!editRole?.id}
                        isProtected={editRole?.protected || false}
                        onSubmit={handleEditRoleSubmit}
                        onCancel={() => setEditRole(null)}
                    />
                </ModalBody>
            </Modal>
            <Modal
                variant={ModalVariant.small}
                isOpen={deleteRole !== null}
                onClose={() => setDeleteRole(null)}
                onEscapePress={() => setDeleteRole(null)}
                aria-labelledby="modal-with-delete-confirmation"
                aria-describedby="modal-box-body-with-delete-confirmation"
            >
                <ModalHeader
                    title={t("confirm-delete-title")}
                    labelId="modal-with-delete-confirmation"
                />
                <ModalBody id="modal-box-body-with-delete-confirmation">
                    <p>
                        {t("confirm-delete-message", {
                            roleName: deleteRole?.name,
                        })}
                    </p>
                </ModalBody>
                <ModalFooter>
                    <ActionList>
                        <ActionListGroup>
                            <ActionListItem>
                                <Button
                                    type="submit"
                                    variant="danger"
                                    onClick={() => {
                                        if (deleteRole) {
                                            handleDeleteRole(deleteRole.id);
                                        }
                                        setDeleteRole(null);
                                    }}
                                >
                                    {t("confirm-delete-button")}
                                </Button>
                            </ActionListItem>
                            <ActionListItem>
                                <Button
                                    variant="link"
                                    onClick={() => setDeleteRole(null)}
                                >
                                    {t("cancel-delete-button")}
                                </Button>
                            </ActionListItem>
                        </ActionListGroup>
                    </ActionList>
                </ModalFooter>
            </Modal>
        </OuterScrollContainer>
    );
};

export default RoleManagement;

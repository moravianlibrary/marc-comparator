import { Fragment, useRef, useState } from "react";
import {
    Dropdown,
    DropdownGroup,
    DropdownList,
    DropdownItem,
    MenuToggle,
    Divider,
    Badge,
} from "@patternfly/react-core";
import { type RoleSummary } from "../../models/api/responses/roles";
import { useTranslation } from "react-i18next";

interface SelectUserRolesProps {
    userRoles: RoleSummary[];
    allRoles: RoleSummary[];
    onAssignRole: (roleId: number) => void;
    onUnassignRole: (roleId: number) => void;
}

const SelectUserRoles = ({
    userRoles,
    allRoles,
    onAssignRole,
    onUnassignRole,
}: SelectUserRolesProps) => {
    const { t } = useTranslation("users");

    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const [selectedRoles, setSelectedRoles] = useState<number[]>(
        userRoles.map((r) => r.id)
    );

    const toggleOpen = () => setIsOpen((prev) => !prev);

    // handle add/remove role
    const handleRoleToggle = (event: any, roleId: number, _: string) => {
        event.stopPropagation();

        const hasRole = selectedRoles.includes(roleId);

        if (hasRole) {
            setSelectedRoles((prev) => prev.filter((id) => id !== roleId));
            onUnassignRole(roleId);
        } else {
            setSelectedRoles((prev) => [...prev, roleId]);
            onAssignRole(roleId);
        }
    };

    return (
        <Dropdown
            isOpen={isOpen}
            onOpenChange={setIsOpen}
            ref={menuRef}
            onActionClick={handleRoleToggle}
            toggle={(toggleRef) => (
                <MenuToggle
                    ref={toggleRef}
                    onClick={toggleOpen}
                    isExpanded={isOpen}
                    badge={
                        <Badge isRead style={{ marginLeft: 8 }}>
                            {selectedRoles.length}
                        </Badge>
                    }
                >
                    {t("edit-roles-menu-placeholder")}
                </MenuToggle>
            )}
            popperProps={{ position: "right" }}
        >
            {selectedRoles.length > 0 && (
                <Fragment>
                    <DropdownGroup
                        key="user-roles"
                        label={t("fields.assigned-roles")}
                    >
                        <DropdownList>
                            {allRoles
                                .filter((r) => selectedRoles.includes(r.id))
                                .map((role) => (
                                    <DropdownItem
                                        key={role.id}
                                        value={role.id}
                                        id={`fav-role-${role.id}`}
                                        isFavorited
                                    >
                                        {role.name}
                                    </DropdownItem>
                                ))}
                        </DropdownList>
                    </DropdownGroup>
                    <Divider key="roles-divider" />
                </Fragment>
            )}
            <DropdownGroup key="roles" label={t("fields.available-roles")}>
                <div
                    style={{
                        maxHeight: "350px",
                        overflowY: "auto",
                        scrollbarGutter: "stable",
                    }}
                >
                    <DropdownList>
                        {allRoles
                            .filter((r) => !selectedRoles.includes(r.id))
                            .map((role) => (
                                <DropdownItem
                                    key={role.id}
                                    value={role.id}
                                    id={`role-${role.id}`}
                                    isFavorited={false}
                                >
                                    {role.name}
                                </DropdownItem>
                            ))}
                    </DropdownList>
                </div>
            </DropdownGroup>
        </Dropdown>
    );
};

export default SelectUserRoles;

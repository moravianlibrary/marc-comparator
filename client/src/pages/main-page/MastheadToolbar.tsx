import {
    Avatar,
    Content,
    Dropdown,
    DropdownItem,
    DropdownList,
    MenuToggle,
    NotificationBadge,
    NotificationBadgeVariant,
    Toolbar,
    ToolbarContent,
    ToolbarGroup,
    ToolbarItem,
    type MenuToggleElement,
} from "@patternfly/react-core";
import { useState, type ReactElement } from "react";
import { useGetMe, useLogout } from "../../hooks/useAuth";
import userAvatar from "@/assets/icons/user-avatar.svg";
import { useNotification } from "../../hooks/useNotifications";
import { useTranslation } from "react-i18next";
import { TaskIcon } from "@patternfly/react-icons";
import { useGetUserActiveTasks } from "../../hooks/useTasks";

const UserActiveTasksNotificationBadge = (): ReactElement | null => {
    const { t } = useTranslation();

    const { data } = useGetUserActiveTasks();

    if (!data) return null;

    const count = data.hits.total.value;

    return (
        <NotificationBadge
            icon={<TaskIcon />}
            // count={getUnreadCount()}
            // variant={
            //     getUnreadCount() === 0
            //         ? NotificationBadgeVariant.read
            //         : notifications.some(
            //               (n) =>
            //                   n.variant === "danger" &&
            //                   !n.isNotificationRead
            //           )
            //         ? NotificationBadgeVariant.attention
            //         : NotificationBadgeVariant.unread
            // }
            // onClick={toggleDrawer}
            isDisabled={count === 0}
            aria-label="Notifications"
        >
            {t("common:running-tasks", { count })}
        </NotificationBadge>
    );
};

const MainPageMastheadToolbar = (): ReactElement => {
    const { t } = useTranslation();
    const { data: me } = useGetMe();
    const logout = useLogout();
    const { notifications, getUnreadCount, toggleDrawer } = useNotification();

    const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);

    return (
        <Toolbar id="toolbar" isStatic>
            <ToolbarContent>
                <ToolbarGroup
                    align={{ default: "alignEnd" }}
                    gap={{ default: "gapXs", md: "gapMd" }}
                    alignItems="center"
                    variant="action-group-inline"
                >
                    <ToolbarItem>
                        {me?.permissions.some((p) =>
                            [
                                "AddRecords",
                                "SyncRecordsFromCatalog",
                                "RunRecordTasks",
                                "SystemMaintenance",
                            ].includes(p)
                        ) ? (
                            <UserActiveTasksNotificationBadge />
                        ) : null}
                    </ToolbarItem>
                    <ToolbarItem>
                        <NotificationBadge
                            count={getUnreadCount()}
                            variant={
                                getUnreadCount() === 0
                                    ? NotificationBadgeVariant.read
                                    : notifications.some(
                                          (n) =>
                                              n.variant === "danger" &&
                                              !n.isNotificationRead
                                      )
                                    ? NotificationBadgeVariant.attention
                                    : NotificationBadgeVariant.unread
                            }
                            onClick={toggleDrawer}
                            isDisabled={notifications.length === 0}
                            aria-label="Notifications"
                        />
                    </ToolbarItem>
                    <ToolbarItem>
                        <Dropdown
                            isOpen={isDropdownOpen}
                            onSelect={() => setIsDropdownOpen(false)}
                            onOpenChange={(isOpen: boolean) =>
                                setIsDropdownOpen(isOpen)
                            }
                            popperProps={{ position: "right" }}
                            toggle={(
                                toggleRef: React.Ref<MenuToggleElement>
                            ) => (
                                <MenuToggle
                                    ref={toggleRef}
                                    onClick={() =>
                                        setIsDropdownOpen(!isDropdownOpen)
                                    }
                                    isExpanded={isDropdownOpen}
                                    icon={
                                        <Avatar
                                            src={userAvatar}
                                            alt=""
                                            size="sm"
                                        />
                                    }
                                >
                                    <Content>{me?.email}</Content>
                                </MenuToggle>
                            )}
                        >
                            <DropdownList>
                                <DropdownItem
                                    key="logout"
                                    onClick={() => logout()}
                                >
                                    {t("auth:logout")}
                                </DropdownItem>
                            </DropdownList>
                        </Dropdown>
                    </ToolbarItem>
                </ToolbarGroup>
            </ToolbarContent>
        </Toolbar>
    );
};

export default MainPageMastheadToolbar;

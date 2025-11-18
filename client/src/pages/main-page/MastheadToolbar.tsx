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

const MainPageMastheadToolbar = (): ReactElement => {
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
                        <NotificationBadge
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
                            disabled={notifications.length === 0}
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
                                    Logout
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

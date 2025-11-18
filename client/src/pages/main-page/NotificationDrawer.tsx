import { type ReactElement } from "react";
import {
    NotificationDrawer,
    NotificationDrawerBody,
    NotificationDrawerHeader,
    NotificationDrawerList,
    NotificationDrawerListItem,
    NotificationDrawerListItemBody,
    NotificationDrawerListItemHeader,
    Content,
    Button,
} from "@patternfly/react-core";
import { useNotification } from "../../hooks/useNotifications";

const AppNotificationDrawer = (): ReactElement => {
    const {
        notifications,
        getUnreadCount,
        markAllNotificationsRead,
        markNotificationRead,
        toggleDrawer,
    } = useNotification();

    return (
        <NotificationDrawer>
            <NotificationDrawerHeader
                count={getUnreadCount()}
                onClose={() => toggleDrawer()}
            >
                <Button variant="link" onClick={markAllNotificationsRead}>
                    Mark all read
                </Button>
            </NotificationDrawerHeader>
            <NotificationDrawerBody>
                {notifications.length === 0 && (
                    <Content>
                        <h6 style={{ marginLeft: "1.5rem" }}>
                            No notifications
                        </h6>
                    </Content>
                )}
                {notifications.length > 0 && (
                    <NotificationDrawerList>
                        {notifications.map((n) => (
                            <NotificationDrawerListItem
                                key={n.key}
                                variant={n.variant}
                                isRead={n.isNotificationRead}
                                onClick={() => markNotificationRead(n.key)}
                            >
                                <NotificationDrawerListItemHeader
                                    variant={n.variant}
                                    title={n.title}
                                    srTitle={n.title}
                                />
                                <NotificationDrawerListItemBody
                                    timestamp={n.timestamp}
                                >
                                    {n.description}
                                </NotificationDrawerListItemBody>
                            </NotificationDrawerListItem>
                        ))}
                    </NotificationDrawerList>
                )}
            </NotificationDrawerBody>
        </NotificationDrawer>
    );
};

export default AppNotificationDrawer;

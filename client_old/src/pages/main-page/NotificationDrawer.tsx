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
import { useTranslation } from "react-i18next";

const AppNotificationDrawer = (): ReactElement => {
    const { t } = useTranslation();
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
                title={t("notifications:title")}
                customText={t("notifications:unread-notifications", {
                    count: getUnreadCount(),
                })}
                onClose={() => toggleDrawer()}
            >
                <Button variant="link" onClick={markAllNotificationsRead}>
                    {t("notifications:mark-all-as-read")}
                </Button>
            </NotificationDrawerHeader>
            <NotificationDrawerBody>
                {notifications.length === 0 && (
                    <Content>
                        <h6 style={{ marginLeft: "1.5rem" }}>
                            {t("notifications:no-notifications")}
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

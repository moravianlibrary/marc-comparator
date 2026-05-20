import React, {
    createContext,
    useContext,
    useState,
    type Key,
    type ReactElement,
    type ReactNode,
} from "react";
import {
    Alert,
    AlertActionCloseButton,
    type AlertProps,
    AlertGroup,
} from "@patternfly/react-core";
import type { Task } from "../models/api/responses/task";

export interface Notification {
    key: Key;
    title: string;
    variant: "custom" | "success" | "danger" | "warning" | "info";
    timestamp: string;
    description: string;
    isNotificationRead: boolean;
}

interface NotificationContextProps {
    notifications: Notification[];
    addNotification: (notification: Notification) => void;
    addTaskCreatedNotification: (taskData: Task) => void;
    markNotificationRead: (key: Key) => void;
    markAllNotificationsRead: () => void;
    getUnreadCount: () => number;
    drawerExpanded: boolean;
    toggleDrawer: () => void;
}

const NotificationContext = createContext<NotificationContextProps | undefined>(
    undefined
);

export const useNotification = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error(
            "useNotification must be used within a NotificationProvider"
        );
    }
    return context;
};

interface NotificationProviderProps {
    children: ReactNode;
}

const NotificationProvider = ({ children }: NotificationProviderProps) => {
    const alertTimeout = 8000;
    const maxDisplayedAlerts = 3;

    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [alerts, setAlerts] = useState<ReactElement<AlertProps>[]>([]);
    const [drawerExpanded, setDrawerExpanded] = useState<boolean>(false);

    const handleCloseAlert = (key: Key) => {
        setAlerts((prev) => prev.filter((alert) => alert.key !== key));
        markNotificationRead(key);
    };

    const addNotification = (notification: Notification) => {
        setNotifications((prev) => [notification, ...prev]);

        if (!drawerExpanded) {
            setAlerts((prev) => [
                <Alert
                    variant={notification.variant}
                    title={notification.title}
                    timeout={alertTimeout}
                    onTimeout={() =>
                        setAlerts((prev) =>
                            prev.filter((a) => a.key !== notification.key)
                        )
                    }
                    isLiveRegion
                    actionClose={
                        <AlertActionCloseButton
                            title={notification.title}
                            variantLabel={`${notification.variant} alert`}
                            onClose={() => handleCloseAlert(notification.key)}
                        />
                    }
                    key={notification.key}
                    id={notification.key.toString()}
                >
                    <p>{notification.description}</p>
                </Alert>,
                ...prev.slice(0, maxDisplayedAlerts - 1),
            ]);
        }
    };

    const addTaskCreatedNotification = (taskData: Task) => {
        addNotification({
            key: `task-created-${taskData.task_id}`,
            title: "Task Created",
            variant: "info",
            timestamp: taskData.created_at.toISOString(),
            description: `A new task ${taskData.name} has been created.`,
            isNotificationRead: false,
        });
    };

    const markNotificationRead = (key: React.Key) => {
        setNotifications((prev) =>
            prev.map((n) =>
                n.key === key ? { ...n, isNotificationRead: true } : n
            )
        );
    };

    const markAllNotificationsRead = () => {
        setNotifications((prev) =>
            prev.map((n) => ({ ...n, isNotificationRead: true }))
        );
    };

    const getUnreadCount = () =>
        notifications.filter((n) => !n.isNotificationRead).length;

    const toggleDrawer = () => setDrawerExpanded((prev) => !prev);

    return (
        <NotificationContext.Provider
            value={{
                notifications,
                addNotification,
                addTaskCreatedNotification,
                markNotificationRead,
                markAllNotificationsRead,
                getUnreadCount,
                drawerExpanded,
                toggleDrawer,
            }}
        >
            {children}
            <AlertGroup hasAnimations isToast isLiveRegion>
                {alerts}
            </AlertGroup>
        </NotificationContext.Provider>
    );
};

export default NotificationProvider;

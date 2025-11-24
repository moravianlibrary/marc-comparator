import { useEffect, useState, type ReactElement } from "react";
import "@patternfly/react-core/dist/styles/base.css";

import { Routes, Route, useNavigate, useLocation } from "react-router";
import {
    Page,
    PageSidebar,
    Nav,
    NavList,
    NavItem,
    PageSidebarBody,
    NavGroup,
    Bullseye,
    Spinner,
} from "@patternfly/react-core";
import { useTranslation } from "react-i18next";
import RecordsTable from "./RecordsTable";
import RecordDetailsSection from "./RecordDetailsSection";
import SystemMaintenance from "./SystemMaintenance";
import RecordsAddition from "./RecordsAddition";
import RoleManagement from "./RoleManagement";
import UserManagement from "./UserManagement";
import TasksTable from "./TasksTable";
import type { EnforcedPermission } from "../models/ui/permissions";
import AccessGuard from "../components/atoms/AccessGuard";
import ProtectedRoute from "../components/atoms/ProtectedRoute";
import MainPageMasthead from "./main-page/Masthead";
import { useGetMe } from "../hooks/useAuth";
import AuthPage from "./AuthPage";
import { useNotification } from "../hooks/useNotifications";
import AppNotificationDrawer from "./main-page/NotificationDrawer";
import CatalogSettingsPage from "./CatalogSettingsPage";
import TasksSettingsPage from "./TaskSettingsPage";
import ValidatorsConfigPage from "./ValidatorsConfigPage";
import ComparatorsConfigPage from "./ComparatorsConfigPage";
import AuthorityLinkersConfigPage from "./AuthorityLinkersConfigPage";

interface NavigationItem {
    itemId: string;
    to: string;
    permission?: EnforcedPermission;
    element: ReactElement;
}

interface NavigationGroup {
    groupId: string;
    permission?: EnforcedPermission;
    items: NavigationItem[];
}

const NAVIGATION_CONFIG: (NavigationGroup | NavigationItem)[] = [
    { itemId: "home", to: "/", element: <div>Home</div> },
    {
        groupId: "records",
        permission: "ReadRecords",
        items: [
            {
                itemId: "table",
                to: "/records/table",
                element: <RecordsTable />,
            },
            // TODO: Low priority - implement dashboard page
            // { itemId: "dashboard", to: "/records/dashboard" },
            {
                itemId: "details",
                to: "/records/details",
                element: <RecordDetailsSection />,
            },
            {
                itemId: "addition",
                to: "/records/addition",
                permission: "AddRecords",
                element: <RecordsAddition />,
            },
        ],
    },
    {
        groupId: "tasks",
        permission: "RunRecordTasks",
        items: [
            { itemId: "table", to: "/tasks/table", element: <TasksTable /> },
            // TODO: Medium priority - implement task traceback page
            // { itemId: "traceback", to: "/tasks/traceback" },
        ],
    },
    {
        groupId: "record-tools",
        permission: "ManageTaskSettings",
        // TODO: High priority - implement record tools pages
        items: [
            {
                itemId: "authority-linkers",
                to: "/record-tools/authority-linkers",
                element: <AuthorityLinkersConfigPage />,
            },
            {
                itemId: "comparators",
                to: "/record-tools/comparators",
                element: <ComparatorsConfigPage />,
            },
            {
                itemId: "validators",
                to: "/record-tools/validators",
                element: <ValidatorsConfigPage />,
            },
        ],
    },
    {
        groupId: "administration",
        permission: {
            any: ["ManageAccessControl", "ManageAppSettings", "ManageSystem"],
        },
        items: [
            {
                itemId: "role-management",
                to: "/administration/role-management",
                permission: "ManageAccessControl",
                element: <RoleManagement />,
            },
            {
                itemId: "user-management",
                to: "/administration/user-management",
                permission: "ManageAccessControl",
                element: <UserManagement />,
            },
            {
                itemId: "catalog-settings",
                to: "/administration/catalog-settings",
                permission: "ManageAppSettings",
                element: <CatalogSettingsPage />,
            },
            {
                itemId: "tasks-settings",
                to: "/administration/tasks-settings",
                permission: "ManageAppSettings",
                element: <TasksSettingsPage />,
            },
            {
                itemId: "system-maintenance",
                to: "/administration/system-maintenance",
                permission: "ManageSystem",
                element: <SystemMaintenance />,
            },
        ],
    },
];

const NAVIGATION_ITEMS_LOOKUP: Record<string, NavigationItem> =
    NAVIGATION_CONFIG.flatMap((entry) =>
        "items" in entry
            ? entry.items.map((i) => ({
                  ...i,
                  itemId: `${entry.groupId}.${i.itemId}`,
              }))
            : [entry]
    ).reduce((acc, item) => {
        acc[item.to] = item;
        return acc;
    }, {} as Record<string, NavigationItem>);

const DEFAULT_ITEM_ID = "home";

const MainPage = (): ReactElement => {
    const { t } = useTranslation();
    const { data: me, isLoading } = useGetMe();
    const { drawerExpanded } = useNotification();
    const navigate = useNavigate();
    const location = useLocation();

    const [activeItem, setActiveItem] = useState<string | number>(
        DEFAULT_ITEM_ID
    );

    useEffect(() => {
        const current = NAVIGATION_ITEMS_LOOKUP[location.pathname];

        if (current) setActiveItem(current.itemId);
    }, [location.pathname]);

    useEffect(() => {
        if (!me && !isLoading) {
            if (location.pathname !== "/login") {
                navigate(
                    "/login?redirect=" + encodeURIComponent(location.pathname)
                );
            } else {
                navigate("/login");
            }
        }
    }, [me, isLoading, navigate]);

    const onNavSelect = (
        event: React.FormEvent<HTMLInputElement>,
        { itemId, to }: { itemId: string | number; to: string }
    ) => {
        event.preventDefault();
        setActiveItem(itemId);
        navigate(to);
    };

    const navItem = (item: NavigationItem, groupId?: string) => {
        const itemId = groupId ? `${groupId}.${item.itemId}` : item.itemId;
        return (
            <AccessGuard key={itemId} permission={item.permission}>
                <NavItem
                    key={itemId}
                    itemId={itemId}
                    to={item.to}
                    isActive={activeItem === itemId}
                >
                    {t(`navbar:${itemId}`)}
                </NavItem>
            </AccessGuard>
        );
    };

    const navSection = (group: NavigationGroup) => {
        return (
            <AccessGuard key={group.groupId} permission={group.permission}>
                <NavGroup
                    key={group.groupId}
                    title={t(`navbar:${group.groupId}.group-title`)}
                >
                    {group.items.map((item) => navItem(item, group.groupId))}
                </NavGroup>
            </AccessGuard>
        );
    };

    const sidebar = (
        <PageSidebar>
            <PageSidebarBody>
                <Nav onSelect={onNavSelect}>
                    <NavList>
                        {NAVIGATION_CONFIG.map((entry) =>
                            "groupId" in entry
                                ? navSection(entry)
                                : navItem(entry)
                        )}
                    </NavList>
                </Nav>
            </PageSidebarBody>
        </PageSidebar>
    );

    if (isLoading) {
        return (
            <div style={{ height: "100vh" }}>
                <Bullseye>
                    <Spinner size="xl" />
                </Bullseye>
            </div>
        );
    }

    if (!me) {
        return <AuthPage />;
    }

    return (
        <Page
            masthead={<MainPageMasthead />}
            sidebar={sidebar}
            notificationDrawer={<AppNotificationDrawer />}
            isNotificationDrawerExpanded={drawerExpanded}
            isManagedSidebar
        >
            <Routes>
                {NAVIGATION_CONFIG.flatMap((entry) =>
                    "groupId" in entry ? entry.items : [entry]
                ).map((item, index) => (
                    <Route
                        key={index}
                        path={item.to}
                        element={
                            <ProtectedRoute
                                permission={item.permission}
                                element={item.element}
                            />
                        }
                    />
                ))}
            </Routes>
        </Page>
    );
};

export default MainPage;

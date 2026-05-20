import type { AppMenuEntry } from "./appMenu.types";
import { hasPermission } from "./userGuards";

import HomePage from "../pages/Home";
import RecordsTable from "../pages/RecordsTable";
import RecordDetailsSection from "../pages/RecordDetailsSection";
import RecordsAddition from "../pages/RecordsAddition";
import TasksTable from "../pages/TasksTable";
import TasksDetailsPage from "../pages/TaskDetails";
import SystemMaintenance from "../pages/SystemMaintenance";
import RoleManagement from "../pages/RoleManagement";
import UserManagement from "../pages/UserManagement";
import CatalogSettingsPage from "../pages/CatalogSettingsPage";
import TasksSettingsPage from "../pages/TaskSettingsPage";
import ValidatorsConfigPage from "../pages/ValidatorsConfigPage";
import ComparatorsConfigPage from "../pages/ComparatorsConfigPage";
import AuthorityLinkersConfigPage from "../pages/AuthorityLinkersConfigPage";

/** Example: admin area needs any of these permissions (OR). */
const administrationGate = hasPermission({
    any: [
        "ManageAccessControl",
        "ManageAppSettings",
        "ManageSystem",
    ],
});

/**
 * Application menu & routes. Groups use `prefix` + child `path` → full URL.
 * Section `guard: null` inherits the group guard.
 * For custom rules use `hasPermission(...)` with `{ any: [...] }` / `{ all: [...] }`.
 */
export const appSections: AppMenuEntry[] = [
    {
        type: "section",
        id: "home",
        path: "/",
        component: HomePage,
        guard: null,
    },
    {
        type: "group",
        id: "records",
        prefix: "/records",
        guard: hasPermission("ReadRecords"),
        children: [
            {
                type: "section",
                id: "table",
                path: "table",
                component: RecordsTable,
                guard: null,
            },
            {
                type: "section",
                id: "details",
                path: "details",
                component: RecordDetailsSection,
                guard: null,
            },
            {
                type: "section",
                id: "addition",
                path: "addition",
                component: RecordsAddition,
                guard: hasPermission("AddRecords"),
            },
        ],
    },
    {
        type: "group",
        id: "tasks",
        prefix: "/tasks",
        guard: hasPermission("RunRecordTasks"),
        children: [
            {
                type: "section",
                id: "table",
                path: "table",
                component: TasksTable,
                guard: null,
            },
            {
                type: "section",
                id: "details",
                path: "details",
                component: TasksDetailsPage,
                guard: null,
            },
        ],
    },
    {
        type: "group",
        id: "record-tools",
        prefix: "/record-tools",
        guard: hasPermission("ManageTaskSettings"),
        children: [
            {
                type: "section",
                id: "authority-linkers",
                path: "authority-linkers",
                component: AuthorityLinkersConfigPage,
                guard: null,
            },
            {
                type: "section",
                id: "comparators",
                path: "comparators",
                component: ComparatorsConfigPage,
                guard: null,
            },
            {
                type: "section",
                id: "validators",
                path: "validators",
                component: ValidatorsConfigPage,
                guard: null,
            },
        ],
    },
    {
        type: "group",
        id: "administration",
        prefix: "/administration",
        guard: administrationGate,
        children: [
            {
                type: "section",
                id: "role-management",
                path: "role-management",
                component: RoleManagement,
                guard: hasPermission("ManageAccessControl"),
            },
            {
                type: "section",
                id: "user-management",
                path: "user-management",
                component: UserManagement,
                guard: hasPermission("ManageAccessControl"),
            },
            {
                type: "section",
                id: "catalog-settings",
                path: "catalog-settings",
                component: CatalogSettingsPage,
                guard: hasPermission("ManageAppSettings"),
            },
            {
                type: "section",
                id: "tasks-settings",
                path: "tasks-settings",
                component: TasksSettingsPage,
                guard: hasPermission("ManageAppSettings"),
            },
            {
                type: "section",
                id: "system-maintenance",
                path: "system-maintenance",
                component: SystemMaintenance,
                guard: hasPermission("ManageSystem"),
            },
        ],
    },
];

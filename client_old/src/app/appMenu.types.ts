import type { ComponentType, ReactNode } from "react";
import type { UserGuard } from "./userGuards";

/** Wraps `<Outlet />` for a route group (e.g. shared state provider). */
export type AppOutletWrapper = ComponentType<{ children: ReactNode }>;

/**
 * Leaf route. At the root of `appSections` use an absolute `path` (e.g. `/`).
 * Inside a group, `path` is relative to the group `prefix` (e.g. `table` → `/records/table`).
 */
export interface AppMenuSection {
    type: "section";
    id: string;
    path: string;
    component: ComponentType;
    /** `null` = only the group guard applies (combined with AND). */
    guard: UserGuard | null;
}

/** Group of routes under `prefix`; optional wrapper for nested `<Outlet />`. */
export interface AppMenuGroup {
    type: "group";
    /** Nav item ids: `${id}.${child.id}`; group title: `navbar:${id}.group-title`. */
    id: string;
    /** URL prefix, e.g. `/records` (no trailing slash). */
    prefix: string;
    guard: UserGuard | null;
    children: AppMenuSection[];
    outletWrapper?: AppOutletWrapper;
}

export type AppMenuEntry = AppMenuGroup | AppMenuSection;

import type { ReactElement } from "react";
import { Routes, Route, Navigate, Outlet } from "react-router";
import type { Me } from "../models/api/responses/users";
import { appSections } from "../app/appSections";
import {
    joinMenuPaths,
    routeParentSegment,
} from "../app/appMenu.utils";
import type { AppMenuEntry, AppMenuGroup } from "../app/appMenu.types";
import GuardedRoute from "../components/atoms/GuardedRoute";

/** React Router `path` prop (no leading slash except root). */
function pathPattern(fullPath: string): string {
    if (fullPath === "/") return "/";
    return fullPath.replace(/^\//, "");
}

function menuEntryToRoutes(entry: AppMenuEntry, user: Me): ReactElement[] {
    if (entry.type === "section") {
        const C = entry.component;
        return [
            <Route
                key={entry.id}
                path={pathPattern(entry.path)}
                element={
                    <GuardedRoute
                        guard={entry.guard}
                        user={user}
                        element={<C />}
                    />
                }
            />,
        ];
    }

    const group = entry as AppMenuGroup;

    const isAllowed = (guard: typeof group.guard) => {
        if (guard == null) return true;
        return guard(user);
    };

    if (group.outletWrapper) {
        const W = group.outletWrapper;
        const parentSeg = routeParentSegment(group.prefix);
        const firstAllowedChild =
            group.children.find((child) => isAllowed(child.guard ?? group.guard)) ??
            group.children[0];
        const defaultChild = firstAllowedChild?.path.replace(/^\//, "") ?? "table";

        return [
            <Route
                key={group.id}
                path={parentSeg}
                element={
                    <W>
                        <Outlet />
                    </W>
                }
            >
                <Route
                    index
                    element={<Navigate to={defaultChild} replace />}
                />
                {group.children.map((child) => {
                    const C = child.component;
                    const rel = child.path.replace(/^\//, "");
                    const effectiveGuard = child.guard ?? group.guard;
                    return (
                        <Route
                            key={`${group.id}.${child.id}`}
                            path={rel}
                            element={
                                <GuardedRoute
                                    guard={effectiveGuard}
                                    user={user}
                                    element={<C />}
                                />
                            }
                        />
                    );
                })}
            </Route>,
        ];
    }

    const fullPrefix = pathPattern(group.prefix);
    const firstAllowedChild =
        group.children.find((child) => isAllowed(child.guard ?? group.guard)) ??
        group.children[0];
    const defaultPath = joinMenuPaths(
        group.prefix,
        firstAllowedChild?.path ?? "table"
    );

    const out: ReactElement[] = [
        <Route
            key={`${group.id}.__redirect`}
            path={fullPrefix}
            element={<Navigate to={defaultPath} replace />}
        />,
    ];

    for (const child of group.children) {
        const full = joinMenuPaths(group.prefix, child.path);
        const C = child.component;
        const effectiveGuard = child.guard ?? group.guard;
        out.push(
            <Route
                key={`${group.id}.${child.id}`}
                path={pathPattern(full)}
                element={
                    <GuardedRoute
                        guard={effectiveGuard}
                        user={user}
                        element={<C />}
                    />
                }
            />
        );
    }

    return out;
}

export default function AppLayoutRoutes({ user }: { user: Me }): ReactElement {
    return (
        <Routes>
            {appSections.flatMap((entry) => menuEntryToRoutes(entry, user))}
        </Routes>
    );
}

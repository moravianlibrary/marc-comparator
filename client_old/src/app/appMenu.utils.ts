import type { AppMenuEntry, AppMenuGroup, AppMenuSection } from "./appMenu.types";

/** `/admin` + `users` → `/admin/users`; `/admin` + `/users` → `/admin/users`. */
export function joinMenuPaths(prefix: string, segment: string): string {
    const a = prefix.replace(/\/$/, "");
    const b = segment.replace(/^\//, "");
    return `${a}/${b}`;
}

/** Parent path segment for React Router nested `path` (e.g. `/records` → `records`). */
export function routeParentSegment(prefix: string): string {
    return prefix.replace(/^\//, "").replace(/\/$/, "");
}

export type FlatNavItem = { path: string; itemId: string };

export function flattenMenuForNav(entries: AppMenuEntry[]): FlatNavItem[] {
    return entries.flatMap((entry) => {
        if (entry.type === "group") {
            return entry.children.map((child) => ({
                path: joinMenuPaths(entry.prefix, child.path),
                itemId: `${entry.id}.${child.id}`,
            }));
        }
        return [{ path: entry.path, itemId: entry.id }];
    });
}

export function isAppMenuGroup(entry: AppMenuEntry): entry is AppMenuGroup {
    return entry.type === "group";
}

export function isAppMenuSection(entry: AppMenuEntry): entry is AppMenuSection {
    return entry.type === "section";
}

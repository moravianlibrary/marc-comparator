import type { Me } from "../models/api/responses/users";
import type { EnforcedPermission } from "../models/ui/permissions";

/** Pure function: true if the user may access the resource. */
export type UserGuard = (user: Me | null | undefined) => boolean;

/** Always allow (e.g. public home). */
export const allowAll: UserGuard = () => true;

/** Require authenticated user (any Me). */
export const isAuthenticated: UserGuard = (user) => user != null;

function checkEnforcedPermission(
    user: Me,
    permission: EnforcedPermission
): boolean {
    if (typeof permission === "object") {
        if ("any" in permission) {
            return permission.any.some((p) => user.permissions.includes(p));
        }
        if ("all" in permission) {
            return permission.all.every((p) => user.permissions.includes(p));
        }
    }
    return user.permissions.includes(permission);
}

/** Guard from a single permission or `{ any: [...] }` / `{ all: [...] }`. */
export function hasPermission(permission: EnforcedPermission): UserGuard {
    return (user) => {
        if (!user) return false;
        return checkEnforcedPermission(user, permission);
    };
}

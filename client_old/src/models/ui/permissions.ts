import type { Permission } from "../primitives/permissions";

export type EnforcedPermission =
    | Permission
    | { any: Permission[] }
    | { all: Permission[] };

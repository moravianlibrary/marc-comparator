import { z } from "zod";

export const PermissionSchema = z.enum([
    "Read",
    "Write",
    "Hide",
    "Validate",
    "Pair",
    "Compare",
    "Admin",
]);
export type Permission = z.infer<typeof PermissionSchema>;
export const PermissionsSchema = z.array(PermissionSchema);
export type Permissions = z.infer<typeof PermissionsSchema>;

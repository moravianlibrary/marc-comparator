import { z } from "zod";
import { PermissionsSchema } from "../../primitives/permissions";

export const EditRoleSchema = z.object({
    name: z.string().min(1, "Role name cannot be empty"),
    permissions: PermissionsSchema,
});
export type EditRole = z.infer<typeof EditRoleSchema>;

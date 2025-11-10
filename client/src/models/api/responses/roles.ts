import { z } from "zod";
import { PermissionsSchema } from "../../primitives/permissions";
import { createPageSchema } from "./pagination";

export const RoleResponseSchema = z.object({
    id: z.number(),
    name: z.string(),
    permissions: PermissionsSchema,
    immutable: z.boolean(),
    protected: z.boolean(),
});
export type RoleResponse = z.infer<typeof RoleResponseSchema>;

export const RolesPageSchema = createPageSchema(RoleResponseSchema);
export type RolesPage = z.infer<typeof RolesPageSchema>;

export const RoleSummarySchema = RoleResponseSchema.pick({
    id: true,
    name: true,
});
export type RoleSummary = z.infer<typeof RoleSummarySchema>;

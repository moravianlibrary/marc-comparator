import { z } from "zod";
import { EditRoleSchema } from "../requests/auth";

export const TokenSchema = z.object({
    access_token: z.string(),
    token_type: z.string(),
});
export type Token = z.infer<typeof TokenSchema>;

export const RoleSchema = EditRoleSchema.extend({
    id: z.string(),
});
export type Role = z.infer<typeof RoleSchema>;

export const UserInfoSchema = z.object({
    id: z.string(),
    email: z.email(),
    first_name: z.string(),
    last_name: z.string(),
    roles: z.array(z.string()),
});
export type UserInfo = z.infer<typeof UserInfoSchema>;

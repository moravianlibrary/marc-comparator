import { z } from "zod";
import { createPageSchema } from "./pagination";
import { RoleSummarySchema } from "./roles";

export const UserIdSchema = z.uuidv4();
export type UserId = z.infer<typeof UserIdSchema>;

export const UserSchema = z.object({
    id: z.uuidv4(),
    email: z.email(),
    first_name: z.string(),
    last_name: z.string(),
    roles: z.array(RoleSummarySchema),
});
export type User = z.infer<typeof UserSchema>;

export const UsersPageSchema = createPageSchema(UserSchema);
export type UsersPage = z.infer<typeof UsersPageSchema>;

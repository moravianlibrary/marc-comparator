import { z } from "zod";
import { RoleSummarySchema } from "./roles";

export const TokenSchema = z.object({
    access_token: z.string(),
    token_type: z.string(),
});
export type Token = z.infer<typeof TokenSchema>;

export const UserInfoSchema = z.object({
    id: z.string(),
    email: z.email(),
    first_name: z.string(),
    last_name: z.string(),
    roles: z.array(RoleSummarySchema),
});
export type UserInfo = z.infer<typeof UserInfoSchema>;

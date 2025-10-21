import { z } from "zod";
import { PermissionsSchema } from "../../primitives/auth";

export const RegisterUserSchema = z.object({
    email: z.email(),
    first_name: z.string(),
    last_name: z.string(),
    password: z
        .string()
        .min(8, { message: "Password must be at least 8 characters long" }),
});
export type RegisterUser = z.infer<typeof RegisterUserSchema>;

export const LoginUserSchema = z.object({
    email: z.email(),
    password: z.string(),
});
export type LoginUser = z.infer<typeof LoginUserSchema>;

export const EditRoleSchema = z.object({
    name: z.string(),
    permissions: PermissionsSchema,
});
export type EditRole = z.infer<typeof EditRoleSchema>;

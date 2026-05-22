import { z } from "zod";
import i18n from "@/lib/i18n";

export const loginSchema = z.object({
  email: z.email(),
  password: z.string().min(1),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const signupSchema = z
  .object({
    email: z.email(),
    first_name: z.string().min(1),
    last_name: z.string().min(1),
    password: z.string().min(8),
    confirm_password: z.string().min(8),
  })
  .refine((data) => data.password === data.confirm_password, {
    path: ["confirm_password"],
    message: i18n.t("validation.passwords-mismatch"),
  });

export type SignupFormValues = z.infer<typeof signupSchema>;

import { z } from "zod";

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
    message: "Hesla se neshodují",
  });

export type SignupFormValues = z.infer<typeof signupSchema>;

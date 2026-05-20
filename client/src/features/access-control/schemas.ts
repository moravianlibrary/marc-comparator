import { z } from "zod";

export const roleSchema = z.object({
  name: z.string().min(4),
  permissions: z.array(z.string()).min(1),
});

export type RoleFormValues = z.infer<typeof roleSchema>;

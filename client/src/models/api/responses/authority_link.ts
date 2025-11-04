import { z } from "zod";

export const AuthorityLinkSchema = z.object({
    linker: z.string(),
    base: z.string(),
    system_number: z.string(),
    confidence: z.number().nullable(),
    updated_at: z.date(),
});
export type AuthorityLink = z.infer<typeof AuthorityLinkSchema>;

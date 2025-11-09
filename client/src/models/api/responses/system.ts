import { z } from "zod";

export const AuthorityLinkerInfoSchema = z.object({
    name: z.string(),
    target_bases: z.array(z.string()),
});

export const SystemInfoSchema = z.object({
    system_version: z.string(),
    system_commit: z.string(),
    uptime_seconds: z.number(),
    available_bases: z.array(z.string()),
    enabled_authority_linkers: z.array(AuthorityLinkerInfoSchema),
    enabled_comparators: z.array(z.string()),
    enabled_validators: z.array(z.string()),
});
export type SystemInfo = z.infer<typeof SystemInfoSchema>;

export const ValidationTargetSchema = z.object({
    tag: z.string().regex(/^\d{3}$/),
    codes: z.array(z.string()).optional(),
});
export type ValidationTarget = z.infer<typeof ValidationTargetSchema>;

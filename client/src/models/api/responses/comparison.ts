import { z } from "zod";

export const ComparisonTargetSchema = z.object({
    tag: z.string().regex(/^\d{3}$/),
    codes: z.array(z.string()).optional(),
    score: z.number(),
    reason: z.string().optional(),
    details: z.string().optional(),
});
export type ComparisonTarget = z.infer<typeof ComparisonTargetSchema>;

export const ComparisonResultSchema = z.object({
    base: z.string(),
    system_number: z.string(),
    overall_score: z.number(),
    summary: z.string().optional(),
    targets: z.array(ComparisonTargetSchema).optional(),
});
export type ComparisonResult = z.infer<typeof ComparisonResultSchema>;

import { z } from "zod";

export const SubfieldComparisonResultSchema = z.object({
    code: z.string().length(1),
    idxA: z.number().optional(),
    idxB: z.number().optional(),
    score: z.number(),
    explanation: z.string().optional(),
    details: z.string().optional(),
});
export type SubfieldComparisonResult = z.infer<
    typeof SubfieldComparisonResultSchema
>;

export const FieldComparisonResultSchema = z.object({
    tag: z.string().regex(/^\d{3}$/),
    idxA: z.number().optional(),
    idxB: z.number().optional(),
    score: z.number(),
    explanation: z.string().optional(),
    details: z.string().optional(),
    subfield_results: z.array(SubfieldComparisonResultSchema).optional(),
});
export type FieldComparisonResult = z.infer<typeof FieldComparisonResultSchema>;

export const ComparisonSchema = z.object({
    comparator: z.string(),
    base: z.string(),
    system_number: z.string(),
    overall_score: z.number(),
    summary: z.string().optional(),
    field_results: z.array(FieldComparisonResultSchema).optional(),
    updated_at: z.coerce.date(),
});
export type Comparison = z.infer<typeof ComparisonSchema>;

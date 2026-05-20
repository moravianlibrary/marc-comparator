import { z } from "zod";
import { MatchQualitySchema } from "../../primitives/comparison";

export const SubfieldComparisonResultSchema = z.object({
    code: z.string().length(1),
    idxA: z.number().optional().nullable(),
    idxB: z.number().optional().nullable(),
    score: z.number(),
    explanation: z.string().optional().nullable(),
    details: z.string().optional().nullable(),
});
export type SubfieldComparisonResult = z.infer<
    typeof SubfieldComparisonResultSchema
>;

export const FieldComparisonResultSchema = z.object({
    tag: z.string().regex(/^\d{3}$/),
    tagB: z
        .string()
        .regex(/^\d{3}$/)
        .optional()
        .nullable(),
    idxA: z.number().optional().nullable(),
    idxB: z.number().optional().nullable(),
    score: z.number(),
    explanation: z.string().optional().nullable(),
    details: z.string().optional().nullable(),
    subfield_results: z
        .array(SubfieldComparisonResultSchema)
        .optional()
        .nullable(),
});
export type FieldComparisonResult = z.infer<typeof FieldComparisonResultSchema>;

export const ComparisonSchema = z.object({
    comparator: z.string(),
    base: z.string(),
    system_number: z.string(),
    match_quality: MatchQualitySchema,
    overall_score: z.number(),
    summary: z.string().optional().nullable(),
    field_results: z.array(FieldComparisonResultSchema).optional().nullable(),
    updated_at: z.coerce.date(),
});
export type Comparison = z.infer<typeof ComparisonSchema>;

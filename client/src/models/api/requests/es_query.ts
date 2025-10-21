import { z } from "zod";

/* --- multi_match --- */
export const MultiMatchQuerySchema = z.object({
    query: z.union([z.string(), z.number(), z.boolean()]),
    fields: z.array(z.string()).optional(),
    type: z
        .union([
            z.literal("best_fields"),
            z.literal("most_fields"),
            z.literal("cross_fields"),
            z.literal("phrase"),
            z.literal("phrase_prefix"),
            z.literal("bool_prefix"),
        ])
        .optional(),
    fuzziness: z.string().optional(),
    prefix_length: z.number().optional(),
    max_expansions: z.number().optional(),
    tie_breaker: z.number().optional(),
    cutoff_frequency: z.number().optional(),
    analyzer: z.string().optional(),
    operator: z.enum(["and", "or"]).optional(),
    minimum_should_match: z.union([z.string(), z.number()]).optional(),
    lenient: z.boolean().optional(),
    zero_terms_query: z.enum(["none", "all"]).optional(),
    boost: z.number().optional(),
});

/* --- bool (recursive) --- */
export const BoolQuerySchema: z.ZodType<any> = z.lazy(() =>
    z.object({
        must: z.union([z.array(EsQuerySchema), EsQuerySchema]).optional(),
        filter: z.union([z.array(EsQuerySchema), EsQuerySchema]).optional(),
        should: z.union([z.array(EsQuerySchema), EsQuerySchema]).optional(),
        must_not: z.union([z.array(EsQuerySchema), EsQuerySchema]).optional(),
        minimum_should_match: z.union([z.string(), z.number()]).optional(),
        boost: z.number().optional(),
    })
);

/* --- Query schema --- */

export const EsQuerySchema = z.lazy(() =>
    z.union([
        z.object({ multi_match: MultiMatchQuerySchema }),
        z.object({ bool: BoolQuerySchema }),
        z.any(), // fallback for other queries if needed
    ])
);
export type EsQuery = z.infer<typeof EsQuerySchema>;

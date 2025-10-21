import { z } from "zod";
import { EsQuerySchema } from "./es_query";

/* --- Aggregation request schemas --- */

export const EsTermsAggRequestSchema = z.object({
    field: z.string(),
    size: z.number().optional(),
    include: z.union([z.string(), z.array(z.string())]).optional(),
    exclude: z.union([z.string(), z.array(z.string())]).optional(),
    order: z.object({ _count: z.enum(["desc", "asc"]).optional() }).optional(),
});
export type EsTermsAggRequest = z.infer<typeof EsTermsAggRequestSchema>;

export const EsRangeAggRequestSchema = z.object({
    field: z.string(),
    ranges: z.array(
        z.object({
            key: z.string().optional(),
            from: z.number().nullable().optional(),
            to: z.number().nullable().optional(),
        })
    ),
});
export type EsRangeAggRequest = z.infer<typeof EsRangeAggRequestSchema>;

export const EsDateRangeAggRequestSchema = z.object({
    field: z.string(),
    format: z.string().optional(),
    ranges: z.array(
        z.object({
            key: z.string().optional(),
            from: z.union([z.string(), z.number()]).nullable().optional(),
            to: z.union([z.string(), z.number()]).nullable().optional(),
        })
    ),
});
export type EsDateRangeAggRequest = z.infer<typeof EsDateRangeAggRequestSchema>;

export const EsAggregationsRequestSchema = z.union([
    z.object({ terms: EsTermsAggRequestSchema }),
    z.object({ range: EsRangeAggRequestSchema }),
    z.object({ date_range: EsDateRangeAggRequestSchema }),
]);
export type EsAggregationsRequest = z.infer<typeof EsAggregationsRequestSchema>;

/* --- Request schema --- */

export const EsSortOrderSchema = z.enum(["asc", "desc"]).default("desc");
export type EsSortOrder = z.infer<typeof EsSortOrderSchema>;

export const EsSortBySchema = z.array(
    z.object({
        field: z.string(),
        order: EsSortOrderSchema,
    })
);
export type EsSortBy = z.infer<typeof EsSortBySchema>;

export const EsRequestSchema = z.object({
    query: EsQuerySchema,
    from: z.number().min(0).optional(),
    size: z.number().min(1).max(1000).optional(),
    sort: EsSortBySchema.optional(),
    _source: z
        .object({
            includes: z.array(z.string()).optional(),
            excludes: z.array(z.string()).optional(),
        })
        .optional(),
    aggs: z.record(z.string(), EsAggregationsRequestSchema).optional(),
});
export type EsRequest = z.infer<typeof EsRequestSchema>;

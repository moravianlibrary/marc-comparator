import { z } from "zod";

export const EsBaseBucketSchema = z.object({
    key: z.string().or(z.number()),
    doc_count: z.number(),
});
export type EsBaseBucket = z.infer<typeof EsBaseBucketSchema>;

export const EsTermsBucketSchema = EsBaseBucketSchema.extend({
    key_as_string: z.string().optional(),
});
export type EsTermsBucket = z.infer<typeof EsTermsBucketSchema>;

export const EsRangeBucketSchema = z.object({
    from: z.number().nullable().optional(),
    to: z.number().nullable().optional(),
});
export type EsRangeBucket = z.infer<typeof EsRangeBucketSchema>;

export const EsDateRangeBucketSchema = z.object({
    from: z.union([z.string(), z.number()]).nullable().optional(),
    to: z.union([z.string(), z.number()]).nullable().optional(),
});
export type EsDateRangeBucket = z.infer<typeof EsDateRangeBucketSchema>;

export const EsAggregationBucketSchema = z.union([
    EsTermsBucketSchema,
    EsRangeBucketSchema,
    EsDateRangeBucketSchema,
]);
export type EsAggregationBucket = z.infer<typeof EsAggregationBucketSchema>;

export const EsTermsAggregationSchema = z.object({
    buckets: z.array(EsTermsBucketSchema),
    sum_other_doc_count: z.number().optional(),
    doc_count_error_upper_bound: z.number().optional(),
});
export type EsTermsAggregation = z.infer<typeof EsTermsAggregationSchema>;

export const EsRangeAggregationSchema = z.object({
    buckets: z.array(EsRangeBucketSchema),
});
export type EsRangeAggregation = z.infer<typeof EsRangeAggregationSchema>;

export const EsDateRangeAggregationSchema = z.object({
    buckets: z.array(EsDateRangeBucketSchema),
});
export type EsDateRangeAggregation = z.infer<
    typeof EsDateRangeAggregationSchema
>;

export const EsAggregationSchema = z.union([
    EsTermsAggregationSchema,
    EsRangeAggregationSchema,
    EsDateRangeAggregationSchema,
]);
export type EsAggregation = z.infer<typeof EsAggregationSchema>;

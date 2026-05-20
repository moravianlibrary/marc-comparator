import { z } from "zod";

// Buckets
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
    doc_count: z.number(),
});
export type EsRangeBucket = z.infer<typeof EsRangeBucketSchema>;

export const EsHistogramBucketSchema = z.object({
    key: z.number(),
    doc_count: z.number(),
});
export type EsHistogramBucket = z.infer<typeof EsHistogramBucketSchema>;

export const EsDateRangeBucketSchema = z.object({
    from: z.union([z.string(), z.number()]).nullable().optional(),
    to: z.union([z.string(), z.number()]).nullable().optional(),
    doc_count: z.number(),
});
export type EsDateRangeBucket = z.infer<typeof EsDateRangeBucketSchema>;

// Aggregations
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

export const EsHistogramAggregationSchema = z.object({
    buckets: z.array(EsHistogramBucketSchema),
});
export type EsHistogramAggregation = z.infer<
    typeof EsHistogramAggregationSchema
>;

export const EsDateRangeAggregationSchema = z.object({
    buckets: z.array(EsDateRangeBucketSchema),
});
export type EsDateRangeAggregation = z.infer<
    typeof EsDateRangeAggregationSchema
>;

export const EsAggregationSchema = z.union([
    EsTermsAggregationSchema,
    EsRangeAggregationSchema,
    EsHistogramAggregationSchema,
    EsDateRangeAggregationSchema,
]);
export type EsAggregation = z.infer<typeof EsAggregationSchema>;

// Nested Aggregation
export const EsAggregationContainerSchema: z.ZodType<any> = z.lazy(() =>
    z
        .object({
            doc_count: z.number().optional(),
            sum_other_doc_count: z.number().optional(),
            doc_count_error_upper_bound: z.number().optional(),
            buckets: z
                .array(
                    z.union([
                        EsBaseBucketSchema,
                        EsTermsBucketSchema,
                        EsRangeBucketSchema,
                        EsHistogramBucketSchema,
                        EsDateRangeBucketSchema,
                    ])
                )
                .optional(),
        })
        .catchall(z.union([EsAggregationSchema, EsAggregationContainerSchema]))
);
export type EsAggregationContainer = z.infer<
    typeof EsAggregationContainerSchema
>;

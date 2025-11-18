import { z, type ZodType } from "zod";
import { type EsAggregation, EsAggregationSchema } from "./es_aggregations";

export const createEsHitSchema = <T extends ZodType<any>>(sourceSchema: T) =>
    z.object({
        _index: z.string(),
        _id: z.string(),
        _score: z.number().optional(),
        _source: sourceSchema,
    });
export type EsHit<T> = {
    _index: string;
    _id: string;
    _score?: number;
    _source: Partial<T>;
};

export type EsHits<T> = {
    total: { value: number };
    hits: EsHit<T>[];
};

export type EsResponse<T> = {
    took: number;
    timed_out: boolean;
    _shards: unknown;
    hits: EsHits<T>;
    aggregations?: Record<string, EsAggregation>;
};

export const createEsHitsSchema = <T extends ZodType<any>>(sourceSchema: T) =>
    z.object({
        total: z.object({ value: z.number() }),
        hits: z.array(createEsHitSchema(sourceSchema)),
    });

export const createEsResponseSchema = <T extends ZodType<any>>(
    sourceSchema: T
) =>
    z.object({
        took: z.number(),
        timed_out: z.boolean(),
        _shards: z.any(),
        hits: createEsHitsSchema(sourceSchema),
        aggregations: z.record(z.string(), EsAggregationSchema).optional(),
    });

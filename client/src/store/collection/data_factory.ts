import type { UseQueryResult } from "@tanstack/react-query";
import type { EsHit, EsResponse } from "../../models/api/responses/es";
import type { CollectionData } from "./domain";

function deepMerge(
    a: Record<string, any>,
    b: Record<string, any>
): Record<string, any> {
    const result = { ...a };
    for (const key in b) {
        if (b[key] && typeof b[key] === "object" && !Array.isArray(b[key])) {
            result[key] = deepMerge(result[key] || {}, b[key]);
        } else {
            result[key] = b[key];
        }
    }
    return result;
}

export function buildCollectionData<T>(
    responses: UseQueryResult<EsResponse<T>>[],
    prevData?: CollectionData<T>
): CollectionData<T> {
    const isLoading = responses.some((r) => r.isLoading);
    const isError = responses.some((r) => r.isError);
    const error = responses.find((r) => r.isError)?.error || null;

    if (isLoading) {
        return prevData || { isLoading, isError, error };
    }

    // Main hits response
    const mainHitsResponse = responses.find(
        (r) => r.isSuccess && r.data && r.data.hits?.hits?.length
    );

    const hits: EsHit<T>[] = mainHitsResponse
        ? mainHitsResponse.data!.hits.hits.map((hit: any) => hit)
        : [];

    const totalItems = mainHitsResponse?.data?.hits?.total?.value || 0;

    // First, collect per-field aggregation responses
    const perFieldAggs: Record<string, any> = {};
    const otherAggs: Record<string, any> = {};

    for (const r of responses) {
        if (!r.isSuccess || !r.data?.aggregations) continue;
        const aggs = r.data.aggregations;

        const keys = Object.keys(aggs);

        // If the response contains **only one aggregation**, treat it as per-field
        if (keys.length === 1) {
            const key = keys[0];
            perFieldAggs[key] = aggs[key]; // override any previous
        } else {
            // merge into general aggregations
            Object.assign(otherAggs, aggs);
        }
    }

    // Merge main/general aggregations with per-field overrides
    const aggregations = deepMerge(otherAggs, perFieldAggs);

    return { isLoading, isError, error, hits, totalItems, aggregations };
}

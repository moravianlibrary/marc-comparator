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

    // Extract hits and totalItems only from the main hits response
    const mainHitsResponse = responses.find(
        (r) => r.isSuccess && r.data && r.data.hits?.hits?.length
    );

    const hits: EsHit<T>[] = mainHitsResponse
        ? mainHitsResponse.data!.hits.hits.map((hit: any) => hit)
        : [];

    const totalItems = mainHitsResponse?.data?.hits?.total?.value || 0;

    // Merge aggregations from all responses (including per-filter agg queries)
    const aggregations = responses
        .filter((r) => r.isSuccess && r.data && r.data.aggregations)
        .reduce(
            (acc, r) => deepMerge(acc, r.data!.aggregations!),
            {} as Record<string, any>
        );
    // const aggregations = responses
    //     .filter((r) => r.isSuccess && r.data && r.data.aggregations)
    //     .reduce(
    //         (acc, r) => ({ ...acc, ...r.data!.aggregations }),
    //         {} as Record<string, any>
    //     );

    return { isLoading, isError, error, hits, totalItems, aggregations };
}

import type { UseQueryResult } from "@tanstack/react-query";
import type { EsResponse } from "../../models/api/responses/es";

export function buildCollectionData<T>(
    responses: UseQueryResult<EsResponse<T>, unknown>[]
) {
    const isLoading = responses.some((r) => r.isLoading);
    const isError = responses.some((r) => r.isError);
    const error = responses.find((r) => r.isError)?.error;

    const hits = responses
        .filter((r) => r.isSuccess && r.data)
        .map((r) => r.data?.hits || [])
        .flat()
        .map((hits) => hits.hits || [])
        .flat();

    const totalItems = responses
        .filter((r) => r.isSuccess && r.data)
        .reduce((sum, r) => sum + (r.data?.hits.total.value || 0), 0);

    return { isLoading, isError, error, hits, totalItems };
}

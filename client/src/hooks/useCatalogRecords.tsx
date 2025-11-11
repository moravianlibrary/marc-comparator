import {
    useMutation,
    useQueries,
    useQuery,
    type UseQueryResult,
} from "@tanstack/react-query";
import type { EsRequest } from "../models/api/requests/es";
import type { EsQuery } from "../models/api/requests/es_query";
import type {
    AddBatchOfRecordsData,
    AddOneRecordData,
    SetHiddenStateData,
    SyncRecordsData,
} from "../models/api/requests/catalog_record";
import type { SearchCatalogRecordsResponse } from "../models/api/responses/catalog_record";
import apiClient from "../services/apiClient";
import type { Task } from "../models/api/responses/task";

// -------------------------
// Queries
// -------------------------
export const useSearchCatalogRecords = (request: EsRequest, enabled = true) =>
    useQuery<SearchCatalogRecordsResponse>({
        queryKey: ["catalog-records", "search", request],
        queryFn: async () =>
            (await apiClient.post("/records/search", request)).data,
        enabled,
    });

export const useSearchCatalogRecordsBatch = (
    requests: EsRequest[],
    enabled = true
): UseQueryResult<SearchCatalogRecordsResponse>[] =>
    useQueries({
        queries: requests.map((request, idx) => ({
            queryKey: ["catalog-records", "search", idx, request],
            queryFn: async () =>
                (await apiClient.post("/records/search", request)).data,
            enabled,
        })),
    });

export const useGetAvailableTargetBases = () =>
    useQuery<string[]>({
        queryKey: ["catalog-records", "search", "available-target-bases"],
        queryFn: async () =>
            (
                (
                    await apiClient.post("/records/search", {
                        query: {
                            size: 0,
                            aggs: {
                                distinct_authority_bases: {
                                    nested: {
                                        path: "authority_links",
                                    },
                                    aggs: {
                                        bases: {
                                            terms: {
                                                field: "authority_links.base.keyword",
                                                size: 100,
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    })
                ).data.aggregations?.distinct_authority_bases?.bases?.buckets ??
                []
            ).map((bucket: { key: string }) => bucket.key),
    });

// -------------------------
// Mutations
// -------------------------
export const useAddOneRecord = () =>
    useMutation<Task, Error, AddOneRecordData>({
        mutationFn: async (data: AddOneRecordData) =>
            (await apiClient.post("/records/fetch", data)).data,
    });

export const useAddBatchOfRecords = () =>
    useMutation<Task, Error, AddBatchOfRecordsData>({
        mutationFn: async (data: AddBatchOfRecordsData) =>
            (await apiClient.post("/records/fetch-batch", data)).data,
    });

export const useSyncRecords = () =>
    useMutation<Task, Error, SyncRecordsData>({
        mutationFn: async (data: SyncRecordsData) =>
            (await apiClient.post("/records/sync", data)).data,
    });

export const useReindexRecords = () =>
    useMutation<Task, Error, EsQuery>({
        mutationFn: async (data: EsQuery) =>
            (await apiClient.post("/records/reindex", data)).data,
    });

export const useSetHiddenStateOfRecords = () =>
    useMutation<Task, Error, SetHiddenStateData>({
        mutationFn: async (data) =>
            (await apiClient.post("/records/hide", data)).data,
    });

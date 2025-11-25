import {
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
import {
    SearchCatalogRecordsResponseSchema,
    type CatalogRecord,
    type SearchCatalogRecordsResponse,
} from "../models/api/responses/catalog_record";
import apiClient from "../services/apiClient";
import type { EsHit } from "../models/api/responses/es";
import type { MarcRecord } from "../models/api/responses/marc_record";
import { useCreateTask } from "./useTasks";

// -------------------------
// Queries
// -------------------------
export const useSearchCatalogRecords = (request: EsRequest, enabled = true) =>
    useQuery<SearchCatalogRecordsResponse>({
        queryKey: ["catalog-records", "search", request],
        queryFn: async () =>
            (await apiClient.post("/catalog-records/search", request)).data,
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
                SearchCatalogRecordsResponseSchema.parse(
                    (await apiClient.post("/catalog-records/search", request))
                        .data
                ),
            enabled,
        })),
    });

export const useGetAvailableTargetBases = () =>
    useQuery<string[]>({
        queryKey: ["catalog-records", "search", "available-target-bases"],
        queryFn: async () =>
            (
                (
                    await apiClient.post("/catalog-records/search", {
                        query: {
                            match_all: {},
                        },
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
                    })
                ).data.aggregations?.distinct_authority_bases?.bases?.buckets ??
                []
            ).map((bucket: { key: string }) => bucket.key),
    });

export const useGetCatalogRecordById = (id: string | null, enabled = true) =>
    useQuery<EsHit<CatalogRecord> | null>({
        queryKey: ["catalog-records", "get-by-id", id],
        queryFn: async () => {
            if (!id) return null;

            const response = await apiClient.post<SearchCatalogRecordsResponse>(
                "/catalog-records/search",
                {
                    query: {
                        term: { _id: id },
                    },
                }
            );

            return response.data.hits.hits.length === 1
                ? (response.data.hits.hits[0] as EsHit<CatalogRecord>)
                : null;
        },
        enabled,
    });

export const useGetMarcRecord = (
    base: string,
    systemNumber: string,
    enabled = true
) =>
    useQuery<MarcRecord>({
        queryKey: ["catalog-records", "get-marc-by-id", base, systemNumber],
        queryFn: async () =>
            apiClient
                .get<MarcRecord>(
                    `/catalog-records/${base}/${systemNumber}/marc`
                )
                .then((res) => res.data),
        enabled,
    });

// -------------------------
// Mutations
// -------------------------
export const useAddOneRecord = () =>
    useCreateTask<AddOneRecordData>("/catalog-records/fetch");

export const useAddBatchOfRecords = () =>
    useCreateTask<AddBatchOfRecordsData>("/catalog-records/fetch-batch");

export const useSyncRecords = () =>
    useCreateTask<SyncRecordsData>("/catalog-records/sync");

export const useReindexRecords = () =>
    useCreateTask<EsQuery>("/catalog-records/reindex");

export const useSetHiddenStateOfRecords = () =>
    useCreateTask<SetHiddenStateData>("/catalog-records/hide");

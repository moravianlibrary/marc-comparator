import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import apiClient from "@/lib/api-client";
import { useRecordFilters } from "../use-record-filters";
import type {
  FacetsResponse,
  FacetsPreviewResponse,
  RecordFilter,
} from "../types";

export function useFacets() {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  return useQuery<FacetsResponse>({
    queryKey: ["catalog-records", "facets", recordFilter],
    queryFn: () =>
      apiClient
        .post<FacetsResponse>("/catalog-records/facets", {
          filters: recordFilter,
        })
        .then((r) => r.data),
  });
}

export function useFacetPreview(targetField: string) {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  return useQuery<FacetsPreviewResponse>({
    queryKey: [
      "catalog-records",
      "facets-preview",
      targetField,
      recordFilter,
    ],
    queryFn: () =>
      apiClient
        .post<FacetsPreviewResponse>("/catalog-records/facets-preview", {
          filters: recordFilter,
          target_field: targetField,
        })
        .then((r) => r.data),
    enabled: false,
    staleTime: 30_000,
  });
}

export function usePrefetchFacetPreview() {
  const queryClient = useQueryClient();
  const { buildRecordFilter } = useRecordFilters();

  return useCallback(
    (targetField: string) => {
      const recordFilter = buildRecordFilter();
      queryClient.prefetchQuery({
        queryKey: [
          "catalog-records",
          "facets-preview",
          targetField,
          recordFilter,
        ],
        queryFn: () =>
          apiClient
            .post<FacetsPreviewResponse>("/catalog-records/facets-preview", {
              filters: recordFilter,
              target_field: targetField,
            })
            .then((r) => r.data),
        staleTime: 30_000,
      });
    },
    [queryClient, buildRecordFilter],
  );
}

export function usePreviewForValue(
  targetField: string,
  targetValue: string | null,
): FacetsResponse | undefined {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  const { data } = useQuery<FacetsPreviewResponse>({
    queryKey: [
      "catalog-records",
      "facets-preview",
      targetField,
      recordFilter,
    ],
    enabled: false,
  });

  if (!data || !targetValue) return undefined;

  const entry = data.previews.find((p) => p.target_value === targetValue);
  if (!entry) return undefined;

  return {
    facets: entry.facets,
    histograms: entry.histograms,
    total: entry.total,
  };
}

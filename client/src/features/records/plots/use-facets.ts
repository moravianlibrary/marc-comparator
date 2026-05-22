import { skipToken, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import { useRecordFilters } from "../use-record-filters";
import type { FacetBucket, FacetsResponse, FacetsPreviewResponse } from "../types";

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
    placeholderData: keepPreviousData,
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

  return (targetField: string) => {
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
  };
}

export function usePreviewForValue(
  targetField: string,
  targetValue: string | null,
): FacetsResponse | undefined {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  const { data } = useQuery({
    queryKey: [
      "catalog-records",
      "facets-preview",
      targetField,
      recordFilter,
    ] as const,
    queryFn: skipToken,
  });

  const preview = data as FacetsPreviewResponse | undefined;
  if (!preview || !targetValue) return undefined;

  const entry = preview.previews.find((p) => p.target_value === targetValue);
  if (!entry) return undefined;

  return {
    facets: entry.facets,
    histograms: entry.histograms,
    total: entry.total,
  };
}

/**
 * Eagerly fetches the validators preview and returns per-validator
 * validation_statuses breakdowns. Shares cache with prefetchFacetPreview.
 */
export function usePerValidatorData(): {
  validator: string;
  statuses: FacetBucket[];
  reasons: FacetBucket[];
}[] | undefined {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  const { data } = useQuery<FacetsPreviewResponse>({
    queryKey: [
      "catalog-records",
      "facets-preview",
      "validators",
      recordFilter,
    ],
    queryFn: () =>
      apiClient
        .post<FacetsPreviewResponse>("/catalog-records/facets-preview", {
          filters: recordFilter,
          target_field: "validators",
        })
        .then((r) => r.data),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });

  if (!data) return undefined;

  return data.previews.map((p) => ({
    validator: p.target_value,
    statuses:
      p.facets.find((f) => f.field === "validation_statuses")?.buckets ?? [],
    reasons:
      p.facets.find((f) => f.field === "validation_reasons")?.buckets ?? [],
  }));
}

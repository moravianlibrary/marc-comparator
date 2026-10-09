import { keepPreviousData, skipToken, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { FacetBucket, FacetsPreviewResponse, FacetsResponse } from '../types';
import { useRecordFilters } from '../use-record-filters';

export function useFacets() {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  return useQuery<FacetsResponse>({
    queryKey: ['catalog-records', 'facets', recordFilter],
    queryFn: () =>
      apiClient
        .post<FacetsResponse>('/catalog-records/facets', {
          filters: recordFilter,
        })
        .then(r => r.data),
    placeholderData: keepPreviousData,
  });
}

/**
 * The values a preview was asked for, as a stable part of the cache key.
 *
 * Two requests for the same field differ if they cover different values, and
 * a collapsed pill group covers a different set from an expanded one. Sorted
 * so that the key does not change when only the display order does.
 */
function scopeKey(targetValues?: string[]): string | null {
  return targetValues && targetValues.length > 0 ? [...targetValues].sort().join('\u0000') : null;
}

function previewQueryKey(targetField: string, recordFilter: unknown, targetValues?: string[]) {
  return ['catalog-records', 'facets-preview', targetField, recordFilter, scopeKey(targetValues)];
}

function fetchPreview(targetField: string, recordFilter: unknown, targetValues?: string[]) {
  return apiClient
    .post<FacetsPreviewResponse>('/catalog-records/facets-preview', {
      filters: recordFilter,
      target_field: targetField,
      // Omitted rather than sent empty: the server reads an absent list as
      // "every value", which is what a caller that names none wants.
      ...(targetValues && targetValues.length > 0 ? { target_values: targetValues } : {}),
    })
    .then(r => r.data);
}

export function usePrefetchFacetPreview() {
  const queryClient = useQueryClient();
  const { buildRecordFilter } = useRecordFilters();

  return (targetField: string, targetValues?: string[]) => {
    const recordFilter = buildRecordFilter();
    queryClient.prefetchQuery({
      queryKey: previewQueryKey(targetField, recordFilter, targetValues),
      queryFn: () => fetchPreview(targetField, recordFilter, targetValues),
      staleTime: 30_000,
    });
  };
}

export function usePreviewForValue(
  targetField: string,
  targetValue: string | null,
  targetValues?: string[],
): FacetsResponse | undefined {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  // Reads what the hover already prefetched, so the scope has to be the same
  // one it was fetched under or this looks at an empty slot forever.
  const { data } = useQuery({
    queryKey: previewQueryKey(targetField, recordFilter, targetValues),
    queryFn: skipToken,
  });

  const preview = data as FacetsPreviewResponse | undefined;
  if (!preview || !targetValue) {
    return undefined;
  }

  const entry = preview.previews.find(p => p.target_value === targetValue);
  if (!entry) {
    return undefined;
  }

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
export function usePerValidatorData():
  | {
      validator: string;
      statuses: FacetBucket[];
      reasons: FacetBucket[];
    }[]
  | undefined {
  const { buildRecordFilter } = useRecordFilters();
  const recordFilter = buildRecordFilter();

  const { data } = useQuery<FacetsPreviewResponse>({
    queryKey: previewQueryKey('validators', recordFilter),
    queryFn: () => fetchPreview('validators', recordFilter),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });

  if (!data) {
    return undefined;
  }

  return data.previews.map(p => ({
    validator: p.target_value,
    statuses: p.facets.find(f => f.field === 'validation_statuses')?.buckets ?? [],
    reasons: p.facets.find(f => f.field === 'validation_reasons')?.buckets ?? [],
  }));
}

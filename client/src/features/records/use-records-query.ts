import { keepPreviousData, useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { SearchRecordsRequest, SearchRecordsResponse } from './types';

export function useRecordsSearch(payload: SearchRecordsRequest) {
  return useQuery<SearchRecordsResponse>({
    queryKey: ['catalog-records', 'search', payload],
    queryFn: () =>
      apiClient.post<SearchRecordsResponse>('/catalog-records/search', payload).then(r => r.data),
    placeholderData: keepPreviousData,
  });
}

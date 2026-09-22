import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { HarvestPluginStatus } from '@/types/harvest';
import { isTaskInFlight, RUNNING_POLL_MS } from '../tasks/task-status';

/**
 * Live harvest state per plugin.
 *
 * A running harvest reports progress over the task websocket, but readiness,
 * the record count and the last successful run only change server-side, so
 * poll while a harvest is in flight. The poll stops on its own: the first
 * response without an in-flight task is also the one carrying the new state.
 */
export function useHarvestPlugins() {
  return useQuery<HarvestPluginStatus[]>({
    queryKey: ['harvest', 'plugins'],
    queryFn: () => apiClient.get<HarvestPluginStatus[]>('/harvest/plugins').then(r => r.data),
    refetchInterval: query =>
      (query.state.data ?? []).some(p => p.current_task && isTaskInFlight(p.current_task))
        ? RUNNING_POLL_MS
        : false,
  });
}

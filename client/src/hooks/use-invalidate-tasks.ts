import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';

/**
 * Drops the cached task lists after a task has been created.
 *
 * The `task_status` WS event invalidates them too, but only once a worker has
 * picked the task up. Until then the queued task is missing from a list that
 * react-query still considers fresh, so every form that starts a task calls
 * this on success.
 */
export function useInvalidateTasks() {
  const queryClient = useQueryClient();

  return useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
  }, [queryClient]);
}

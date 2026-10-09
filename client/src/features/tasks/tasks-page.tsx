import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState, useSyncExternalStore } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { SkeletonTable } from '@/components/skeletons/skeleton-table';
import { Button } from '@/components/ui/button';
import { useGetMe } from '@/hooks/use-auth';
import { useHasPermission } from '@/hooks/use-permissions';
import apiClient from '@/lib/api-client';
import { Permission } from '@/types/permission';
import type { Task } from '@/types/task';
import { SYSTEM_USER_ID, type User } from '@/types/user';
import { TaskDetail } from './task-detail';
import { IDLE_POLL_MS, isTaskInFlight, RUNNING_POLL_MS } from './task-status';
import { TaskTable } from './task-table';

const XL_QUERY = '(min-width: 1280px)';
function useIsXl() {
  return useSyncExternalStore(
    cb => {
      const mql = window.matchMedia(XL_QUERY);
      mql.addEventListener('change', cb);
      return () => mql.removeEventListener('change', cb);
    },
    () => window.matchMedia(XL_QUERY).matches,
  );
}

export function TasksPage() {
  const { t } = useTranslation('tasks');
  const queryClient = useQueryClient();
  const { hasPermission } = useHasPermission();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTaskId = searchParams.get('taskId');
  const isXl = useIsXl();
  const pageSize = isXl ? 20 : 15;
  const [page, setPage] = useState(1);

  function handleSelectTask(id: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (next.get('taskId') === id) {
        next.delete('taskId');
      } else {
        next.set('taskId', id);
      }
      return next;
    });
  }

  const canSeeAll = hasPermission(Permission.ManageAllTasks);
  const searchEndpoint = canSeeAll ? '/tasks/search-all' : '/tasks/search-own';

  const { data, isLoading } = useQuery<{ items: Task[]; total: number }>({
    queryKey: ['tasks', 'list', searchEndpoint, page],
    queryFn: () => apiClient.post(searchEndpoint, { page, page_size: pageSize }).then(r => r.data),
    // WS events carry progress but not the rest of the row (severity, counts,
    // finished_at), so poll fast while anything is in flight. Slowly otherwise
    // rather than not at all: a task started after the last fetch is precisely
    // what this data cannot show, so stopping here would freeze the list for
    // good whenever the WS invalidation does not arrive.
    refetchInterval: query =>
      (query.state.data?.items ?? []).some(isTaskInFlight) ? RUNNING_POLL_MS : IDLE_POLL_MS,
    // The list is volatile by nature; the app-wide 5 minute staleTime would
    // otherwise suppress the refetch on mount and on window focus.
    staleTime: 0,
  });

  const { data: usersData } = useQuery<{ items: User[] }>({
    queryKey: ['access-control', 'users'],
    queryFn: () =>
      apiClient
        .get<{ items: User[] }>('/access-control/users', {
          params: { page: 1, page_size: 100 },
        })
        .then(r => r.data),
    // The user list sits behind access control; without it the names below
    // fall back to the viewer's own and to the system account.
    enabled: canSeeAll === true && hasPermission(Permission.ManageAccessControl) === true,
  });

  const { data: me } = useGetMe();
  const userNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of [...(usersData?.items ?? []), ...(me ? [me] : [])]) {
      map.set(u.id, `${u.first_name} ${u.last_name}`.trim() || u.email);
    }
    // Scheduled runs are created by the system account, whose stored name is
    // its placeholder email; say what it is instead.
    map.set(SYSTEM_USER_ID, t('system-user'));
    return map;
  }, [usersData, me, t]);

  const revokeMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.patch(`/tasks/${taskId}/revoke`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const tasks = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);
  const selectedTask = selectedTaskId ? tasks.find(t => t.task_id === selectedTaskId) : undefined;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('title')}</h1>

      <div
        className={`grid gap-4 ${selectedTaskId ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'}`}
      >
        <div className="min-w-0 space-y-4">
          {isLoading ? (
            <SkeletonTable rows={5} columns={7} />
          ) : (
            <div className="animate-fade-in">
              <TaskTable
                tasks={tasks}
                selectedTaskId={selectedTaskId}
                userNames={userNames}
                onSelectTask={handleSelectTask}
                onRevoke={id => revokeMutation.mutate(id)}
              />
            </div>
          )}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {t('common:pagination.page', { page, total: totalPages })}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                >
                  {t('common:pagination.previous')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                >
                  {t('common:pagination.next')}
                </Button>
              </div>
            </div>
          )}
        </div>
        {selectedTaskId && (
          // Fill the viewport below the sticky banner: top-20 clears the banner
          // plus the page padding, and the extra 1.5rem leaves that same padding
          // at the bottom.
          <div className="h-[80vh] min-w-0 xl:sticky xl:top-20 xl:h-[calc(100vh-6.5rem)] xl:self-start">
            <TaskDetail taskId={selectedTaskId} task={selectedTask} />
          </div>
        )}
      </div>
    </div>
  );
}

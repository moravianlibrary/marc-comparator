import { useQuery } from '@tanstack/react-query';
import { CircleHelp, LogOut } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { FontSizeControl } from '@/components/font-size-control';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { useGetMe, useLogout } from '@/hooks/use-auth';
import { useHasPermission } from '@/hooks/use-permissions';
import apiClient from '@/lib/api-client';
import { Permission } from '@/types/permission';
import type { Task } from '@/types/task';
import { IDLE_POLL_MS, RUNNING_POLL_MS } from '@/features/tasks/task-status';
import { HelpDialog } from './help-dialog';
import { MenuPanel } from './menu-panel';
import { TaskProgress } from './task-progress';
import { ToastHistory } from './toast-history';

export function MainBanner() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: me } = useGetMe();
  const logout = useLogout();
  const { hasPermission } = useHasPermission();
  const [showHelp, setShowHelp] = useState(false);

  const canManageTasks = hasPermission(Permission.ManageTasks);

  const { data: tasksData } = useQuery<{ items: Task[] }>({
    queryKey: ['tasks', 'running'],
    queryFn: () =>
      apiClient
        .post<{ items: Task[] }>('/tasks/search-own', {
          filters: { status: ['Started'] },
          page: 1,
          page_size: 20,
        })
        .then(r => r.data),
    enabled: canManageTasks === true,
    // Same reasoning as the task list: "nothing is running" read from this very
    // data cannot reveal a task that started since, so idle means slower rather
    // than never. Otherwise the banner goes quiet for the rest of the session.
    refetchInterval: query =>
      query.state.data?.items?.some(task => task.status === 'Started')
        ? RUNNING_POLL_MS
        : IDLE_POLL_MS,
    staleTime: 0,
  });

  const runningTasks = tasksData?.items ?? [];

  return (
    <>
      <header className="border-b bg-background px-6 py-2 flex items-center gap-4">
        <Button
          variant="ghost"
          className="font-semibold text-lg p-0 h-auto hover:bg-transparent gap-2"
          onClick={() => navigate('/')}
        >
          <img src="/marcomparator-only-logo-transparent.png" alt="" className="h-8 dark:hidden" />
          <img
            src="/marcomparator-only-logo-dark-transparent.png"
            alt=""
            className="h-8 hidden dark:block"
          />
          {t('common:app-name')}
        </Button>

        <MenuPanel />

        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-muted-foreground"
          onClick={() => setShowHelp(true)}
        >
          <CircleHelp className="h-4 w-4" />
          {t('common:menu.help')}
        </Button>

        <div className="flex-1" />

        <TaskProgress runningTasks={runningTasks} />
        <ToastHistory />

        <FontSizeControl />
        <ThemeToggle />

        {me && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {me.first_name} {me.last_name}
            </span>
            <Button
              variant="ghost"
              size="icon"
              title={t('common:user-menu.logout')}
              onClick={() => logout.mutate()}
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </header>
      <HelpDialog open={showHelp} onClose={() => setShowHelp(false)} />
    </>
  );
}

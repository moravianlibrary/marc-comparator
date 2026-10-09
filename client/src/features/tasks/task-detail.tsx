import { useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useHasPermission } from '@/hooks/use-permissions';
import apiClient from '@/lib/api-client';
import { Permission } from '@/types/permission';
import type { ReportArtifact, Task } from '@/types/task';
import { isTaskInFlight, RUNNING_POLL_MS } from './task-status';

/**
 * A run over a large base logs a line per progress step — tens of thousands of
 * them. The end is what anyone actually reads (progress, and the failure), so
 * the panel asks for a window instead of the whole log on every poll.
 */
const TRACEBACK_TAIL_LINES = 2000;

interface TaskDetailProps {
  taskId: string;
  /** The row for this task, when the list beside the panel happens to hold it. */
  task?: Task;
}

export function TaskDetail({ taskId, task }: TaskDetailProps) {
  const { t } = useTranslation('tasks');
  const { hasPermission } = useHasPermission();

  // Opened from a link or a notification, this panel is regularly asked about a
  // task the list beside it does not hold — a later page, another filter, or
  // another user's run. Deciding "is it running" from that list alone left the
  // log of a live task frozen at whatever it said when the panel opened, with
  // no progress bar and nothing saying why. So ask about the task itself.
  const searchEndpoint = hasPermission(Permission.ManageAllTasks)
    ? '/tasks/search-all'
    : '/tasks/search-own';
  const { data: fetchedTask } = useQuery<Task | null>({
    queryKey: ['tasks', 'by-id', searchEndpoint, taskId],
    queryFn: () =>
      apiClient
        .post<{
          items: Task[];
        }>(searchEndpoint, { filters: { task_id: [taskId] }, page: 1, page_size: 1 })
        .then(r => r.data.items[0] ?? null),
    enabled: !task,
    refetchInterval: query =>
      query.state.data && isTaskInFlight(query.state.data) ? RUNNING_POLL_MS : false,
  });

  const current = task ?? fetchedTask ?? undefined;
  const isRunning = current ? isTaskInFlight(current) : false;
  const progress = current?.progress;
  const percent = progress != null ? Math.round(progress * 100) : null;

  const { data: traceback, isLoading } = useQuery<string>({
    queryKey: ['tasks', taskId, 'traceback'],
    queryFn: () =>
      apiClient
        .get<string>(`/tasks/${taskId}/traceback`, { params: { tail: TRACEBACK_TAIL_LINES } })
        .then(r => r.data),
    // The log is what you watch a running task through — keep it in step with
    // the task row rather than a slower cadence of its own.
    refetchInterval: isRunning ? RUNNING_POLL_MS : false,
    staleTime: 0,
  });

  const { data: reports } = useQuery<ReportArtifact[]>({
    // The artifact is committed together with the task's final status, so the
    // last poll while the task runs can never see it — and once the task stops
    // running the poll stops too, leaving the empty answer cached for the
    // app-wide five minutes. Keying on the status asks again the moment the
    // task finishes.
    queryKey: ['reports', taskId, current?.status],
    queryFn: () =>
      apiClient
        .get<ReportArtifact[]>('/reports', { params: { task_id: taskId } })
        .then(r => r.data),
    // Artifacts only appear at the very end, so a slower poll is enough.
    refetchInterval: isRunning ? 5000 : false,
  });

  return (
    <Card className="h-full min-w-0 gap-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-base break-all">
          {t('detail.title')} — {taskId}
        </CardTitle>
        {(percent != null || isRunning) && (
          <div className="flex items-center gap-2">
            <Progress value={percent} className="h-2" />
            <span className="w-9 text-right text-xs tabular-nums text-muted-foreground">
              {percent != null && `${percent}%`}
            </span>
          </div>
        )}
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-4">
        {reports && reports.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {reports.map(report => (
              <Button key={report.id} asChild size="sm" className="max-w-full">
                <a href={`/api/reports/${report.id}/download`} download={report.filename}>
                  <Download className="h-4 w-4" />
                  {t('detail.download')}
                  <span className="truncate font-normal opacity-80">
                    {report.filename} ({Math.round(report.size / 1024)} kB)
                  </span>
                </a>
              </Button>
            ))}
          </div>
        )}
        {isLoading ? (
          <Skeleton className="min-h-0 w-full flex-1 rounded-md" />
        ) : traceback ? (
          // A plain overflow box rather than ScrollArea: Radix wraps the content
          // in a display:table that grows with the longest line, so an unbroken
          // path or URL in the log widened the whole panel past the page.
          <div className="min-h-0 flex-1 overflow-auto rounded-md bg-muted">
            <pre className="whitespace-pre-wrap p-4 font-mono text-xs [overflow-wrap:anywhere]">
              {traceback}
            </pre>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t('detail.no-traceback')}</p>
        )}
      </CardContent>
    </Card>
  );
}

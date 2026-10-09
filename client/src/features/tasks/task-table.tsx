import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { Task } from '@/types/task';
import { taskLabel } from './task-label';

interface TaskTableProps {
  tasks: Task[];
  selectedTaskId: string | null;
  userNames?: Map<string, string>;
  onSelectTask: (taskId: string) => void;
  onRevoke: (taskId: string) => void;
}

const statusVariantMap: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  Pending: 'outline',
  Started: 'default',
  Success: 'secondary',
  Failure: 'destructive',
  Revoked: 'outline',
};

export function TaskTable({
  tasks,
  selectedTaskId,
  userNames,
  onSelectTask,
  onRevoke,
}: TaskTableProps) {
  const { t } = useTranslation('tasks');

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t('fields.type')}</TableHead>
          <TableHead>{t('fields.status')}</TableHead>
          <TableHead>{t('fields.severity')}</TableHead>
          <TableHead>{t('fields.created-at')}</TableHead>
          <TableHead>{t('fields.created-by')}</TableHead>
          <TableHead>{t('fields.run-time')}</TableHead>
          <TableHead>{t('common:actions')}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map(task => (
          <TableRow
            key={task.task_id}
            className={`cursor-pointer ${selectedTaskId === task.task_id ? 'bg-muted' : ''}`}
            onClick={() => onSelectTask(task.task_id)}
          >
            <TableCell className="font-medium">{taskLabel(task, t)}</TableCell>
            <TableCell>
              <Badge variant={statusVariantMap[task.status] ?? 'outline'}>
                {t(`status.${task.status}`)}
              </Badge>
            </TableCell>
            <TableCell>{t(`severity.${task.severity}`)}</TableCell>
            <TableCell className="whitespace-nowrap tabular-nums">
              {new Date(task.created_at).toLocaleString('cs-CZ')}
            </TableCell>
            <TableCell>{userNames?.get(task.created_by) ?? task.created_by}</TableCell>
            <TableCell className="whitespace-nowrap tabular-nums">
              {task.started_at && task.finished_at
                ? formatDuration(task.started_at, task.finished_at)
                : task.started_at
                  ? '...'
                  : '-'}
            </TableCell>
            <TableCell>
              {task.status === 'Started' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={e => {
                    e.stopPropagation();
                    onRevoke(task.task_id);
                  }}
                >
                  {t('fields.revoke')}
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/**
 * A run time, carried up to hours.
 *
 * A harvest or a processing pass runs for hours, and without the larger unit
 * the cell reads "115m 47s" and leaves the reader dividing. Seconds stay at
 * every scale so nothing looks rounded.
 */
function formatDuration(start: string, end: string): string {
  const seconds = Math.floor((new Date(end).getTime() - new Date(start).getTime()) / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return hours > 0
    ? `${hours}h ${minutes}m ${remainingSeconds}s`
    : `${minutes}m ${remainingSeconds}s`;
}

import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Progress } from '@/components/ui/progress';
import { taskLabel } from '@/features/tasks/task-label';
import type { Task } from '@/types/task';

interface TaskProgressProps {
  runningTasks: Task[];
}

export function TaskProgress({ runningTasks }: TaskProgressProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const task = runningTasks[0];
  if (!task) {
    return null;
  }

  if (runningTasks.length === 1) {
    const percent = task.progress != null ? Math.round(task.progress * 100) : null;

    return (
      <button
        type="button"
        className="flex items-center gap-2 cursor-pointer hover:opacity-80"
        onClick={() => navigate(`/tasks?taskId=${task.task_id}`)}
      >
        <span className="text-sm text-muted-foreground truncate max-w-[200px]">
          {taskLabel(task, t)}
        </span>
        <Progress value={percent} className="w-24 h-2" />
        {/* Fixed width and tabular digits: "9%" → "10%" → "100%" must not nudge the bar. */}
        <span className="w-9 text-right text-xs tabular-nums text-muted-foreground">
          {percent != null && `${percent}%`}
        </span>
      </button>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Badge variant="secondary" className="cursor-pointer">
          {t('common:task-progress.running', { count: runningTasks.length })}
        </Badge>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-3">
          {runningTasks.map(task => {
            const percent = task.progress != null ? Math.round(task.progress * 100) : null;

            return (
              <button
                type="button"
                key={task.task_id}
                className="space-y-1 cursor-pointer hover:bg-accent rounded-md p-1 -m-1 w-full text-left"
                onClick={() => navigate(`/tasks?taskId=${task.task_id}`)}
              >
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate">{taskLabel(task, t)}</span>
                  {percent != null && (
                    <span className="tabular-nums text-muted-foreground">{percent}%</span>
                  )}
                </div>
                <Progress value={percent} className="h-2" />
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}

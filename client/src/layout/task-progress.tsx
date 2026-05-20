import { useTranslation } from "react-i18next";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { Task } from "@/types/task";

interface TaskProgressProps {
  runningTasks: Task[];
}

export function TaskProgress({ runningTasks }: TaskProgressProps) {
  const { t } = useTranslation();

  if (runningTasks.length === 0) return null;

  if (runningTasks.length === 1) {
    const task = runningTasks[0];
    const percent =
      task.progress != null && task.total != null && task.total > 0
        ? Math.round((task.progress / task.total) * 100)
        : 0;

    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground truncate max-w-[200px]">
          {task.name}
        </span>
        <Progress value={percent} className="w-24 h-2" />
        <span className="text-xs text-muted-foreground">{percent}%</span>
      </div>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Badge variant="secondary" className="cursor-pointer">
          {t("common:task-progress.running", { count: runningTasks.length })}
        </Badge>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-3">
          {runningTasks.map((task) => {
            const percent =
              task.progress != null && task.total != null && task.total > 0
                ? Math.round((task.progress / task.total) * 100)
                : 0;

            return (
              <div key={task.id} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate">{task.name}</span>
                  <span className="text-muted-foreground">{percent}%</span>
                </div>
                <Progress value={percent} className="h-2" />
              </div>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}

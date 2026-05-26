import { useTranslation } from "react-i18next";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Task } from "@/types/task";

interface TaskTableProps {
  tasks: Task[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  onRevoke: (taskId: string) => void;
}

const statusVariantMap: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  Pending: "outline",
  Started: "default",
  Success: "secondary",
  Failure: "destructive",
  Revoked: "outline",
};

export function TaskTable({ tasks, selectedTaskId, onSelectTask, onRevoke }: TaskTableProps) {
  const { t } = useTranslation("tasks");

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("fields.name")}</TableHead>
          <TableHead>{t("fields.status")}</TableHead>
          <TableHead>{t("fields.severity")}</TableHead>
          <TableHead>{t("fields.run-time")}</TableHead>
          <TableHead>{t("common:actions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((task) => (
          <TableRow
            key={task.task_id}
            className={`cursor-pointer ${selectedTaskId === task.task_id ? "bg-muted" : ""}`}
            onClick={() => onSelectTask(task.task_id)}
          >
            <TableCell className="font-medium">{t(`type.${task.type}`)}</TableCell>
            <TableCell>
              <Badge variant={statusVariantMap[task.status] ?? "outline"}>
                {t(`status.${task.status}`)}
              </Badge>
            </TableCell>
            <TableCell>{t(`severity.${task.severity}`)}</TableCell>
            <TableCell>
              {task.started_at && task.finished_at
                ? formatDuration(task.started_at, task.finished_at)
                : task.started_at
                  ? "..."
                  : "-"}
            </TableCell>
            <TableCell>
              {task.status === "Started" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRevoke(task.task_id);
                  }}
                >
                  {t("fields.revoke")}
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function formatDuration(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

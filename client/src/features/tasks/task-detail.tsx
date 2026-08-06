import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Download } from "lucide-react";
import apiClient from "@/lib/api-client";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReportArtifact } from "@/types/task";

interface TaskDetailProps {
  taskId: string;
  isRunning?: boolean;
  progress?: number | null;
}

export function TaskDetail({ taskId, isRunning, progress }: TaskDetailProps) {
  const { t } = useTranslation("tasks");

  const percent = progress != null ? Math.round(progress * 100) : null;

  const { data: traceback, isLoading } = useQuery<string>({
    queryKey: ["tasks", taskId, "traceback"],
    queryFn: () => apiClient.get<string>(`/tasks/${taskId}/traceback`).then((r) => r.data),
    refetchInterval: isRunning ? 5000 : false,
  });

  const { data: reports } = useQuery<ReportArtifact[]>({
    queryKey: ["reports", taskId],
    queryFn: () =>
      apiClient
        .get<ReportArtifact[]>("/reports", { params: { task_id: taskId } })
        .then((r) => r.data),
    refetchInterval: isRunning ? 5000 : false,
  });

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {t("detail.title")} — {taskId}
        </CardTitle>
        {(percent != null || isRunning) && (
          <div className="flex items-center gap-2">
            <Progress value={percent} className="h-2" />
            {percent != null && <span className="text-xs text-muted-foreground">{percent}%</span>}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {reports && reports.length > 0 && (
          <div className="mb-4 space-y-2">
            <p className="text-sm font-medium">{t("detail.reports")}</p>
            <div className="flex flex-col gap-1">
              {reports.map((report) => (
                <a
                  key={report.id}
                  href={`/api/reports/${report.id}/download`}
                  className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
                >
                  <Download className="h-4 w-4" />
                  {report.filename} ({Math.round(report.size / 1024)} kB)
                </a>
              ))}
            </div>
          </div>
        )}
        {isLoading ? (
          <Skeleton className="h-[60vh] w-full rounded-md" />
        ) : traceback ? (
          <ScrollArea className="h-[60vh]">
            <pre className="whitespace-pre-wrap text-xs font-mono bg-muted p-4 rounded-md">
              {traceback}
            </pre>
          </ScrollArea>
        ) : (
          <p className="text-sm text-muted-foreground">{t("detail.no-traceback")}</p>
        )}
      </CardContent>
    </Card>
  );
}

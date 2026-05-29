import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface TaskDetailProps {
  taskId: string;
  isRunning?: boolean;
}

export function TaskDetail({ taskId, isRunning }: TaskDetailProps) {
  const { t } = useTranslation("tasks");

  const { data: traceback, isLoading } = useQuery<string>({
    queryKey: ["tasks", taskId, "traceback"],
    queryFn: () =>
      apiClient
        .get<string>(`/tasks/${taskId}/traceback`)
        .then((r) => r.data),
    refetchInterval: isRunning ? 5000 : false,
  });

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          {t("detail.title")} — {taskId}
          {isRunning && <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-[60vh] w-full rounded-md" />
        ) : traceback ? (
          <ScrollArea className="h-[60vh]">
            <pre className="whitespace-pre-wrap text-xs font-mono bg-muted p-4 rounded-md">
              {traceback}
            </pre>
          </ScrollArea>
        ) : (
          <p className="text-sm text-muted-foreground">
            {t("detail.no-traceback")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

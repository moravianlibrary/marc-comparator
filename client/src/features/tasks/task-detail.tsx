import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface TaskDetailProps {
  taskId: string;
}

export function TaskDetail({ taskId }: TaskDetailProps) {
  const { t } = useTranslation("tasks");

  const { data: traceback, isLoading } = useQuery<string>({
    queryKey: ["tasks", taskId, "traceback"],
    queryFn: () =>
      apiClient
        .get<string>(`/tasks/${taskId}/traceback`)
        .then((r) => r.data),
  });

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {t("detail.title")} — {taskId.slice(0, 8)}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">{t("common:loading")}</p>
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

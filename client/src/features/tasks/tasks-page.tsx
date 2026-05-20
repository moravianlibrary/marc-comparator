import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import type { Task } from "@/types/task";
import { TaskTable } from "./task-table";
import { TaskDetail } from "./task-detail";

export function TasksPage() {
  const { t } = useTranslation("tasks");
  const queryClient = useQueryClient();
  const { hasPermission } = useHasPermission();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const canSeeAll = hasPermission(Permission.ManageAllTasks);
  const searchEndpoint = canSeeAll ? "/tasks/search-all" : "/tasks/search-own";

  const { data, isLoading } = useQuery<{ items: Task[]; total: number }>({
    queryKey: ["tasks", "list", searchEndpoint],
    queryFn: () =>
      apiClient
        .post(searchEndpoint, { page: 1, page_size: 50 })
        .then((r) => r.data),
  });

  const revokeMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.patch(`/tasks/${taskId}/revoke`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const tasks = data?.items ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>

      <div className={`grid gap-4 ${selectedTaskId ? "grid-cols-[1fr_1fr]" : "grid-cols-1"}`}>
        <div>
          {isLoading ? (
            <p className="text-muted-foreground">{t("common:loading")}</p>
          ) : (
            <TaskTable
              tasks={tasks}
              selectedTaskId={selectedTaskId}
              onSelectTask={(id) =>
                setSelectedTaskId((prev) => (prev === id ? null : id))
              }
              onRevoke={(id) => revokeMutation.mutate(id)}
            />
          )}
        </div>
        {selectedTaskId && (
          <div>
            <TaskDetail taskId={selectedTaskId} />
          </div>
        )}
      </div>
    </div>
  );
}

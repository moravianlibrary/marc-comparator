import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import type { Task } from "@/types/task";
import type { User } from "@/types/user";
import { TaskTable } from "./task-table";
import { TaskDetail } from "./task-detail";
import { SkeletonTable } from "@/components/skeletons/skeleton-table";

export function TasksPage() {
  const { t } = useTranslation("tasks");
  const queryClient = useQueryClient();
  const { hasPermission } = useHasPermission();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTaskId = searchParams.get("taskId");

  function handleSelectTask(id: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (next.get("taskId") === id) {
        next.delete("taskId");
      } else {
        next.set("taskId", id);
      }
      return next;
    });
  }

  const canSeeAll = hasPermission(Permission.ManageAllTasks);
  const searchEndpoint = canSeeAll ? "/tasks/search-all" : "/tasks/search-own";

  const { data, isLoading } = useQuery<{ items: Task[]; total: number }>({
    queryKey: ["tasks", "list", searchEndpoint],
    queryFn: () =>
      apiClient
        .post(searchEndpoint, { page: 1, page_size: 50 })
        .then((r) => r.data),
  });

  const { data: usersData } = useQuery<{ items: User[] }>({
    queryKey: ["access-control", "users"],
    queryFn: () =>
      apiClient
        .get<{ items: User[] }>("/access-control/users", {
          params: { page: 1, page_size: 100 },
        })
        .then((r) => r.data),
    enabled: canSeeAll === true,
  });

  const userNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of usersData?.items ?? []) {
      map.set(u.id, `${u.first_name} ${u.last_name}`);
    }
    return map;
  }, [usersData]);

  const revokeMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.patch(`/tasks/${taskId}/revoke`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const tasks = data?.items ?? [];
  const selectedTask = selectedTaskId
    ? tasks.find((t) => t.task_id === selectedTaskId)
    : undefined;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>

      <div className={`grid gap-4 ${selectedTaskId ? "grid-cols-[1fr_1fr]" : "grid-cols-1"}`}>
        <div>
          {isLoading ? (
            <SkeletonTable rows={5} columns={5} />
          ) : (
            <div className="animate-fade-in">
              <TaskTable
                tasks={tasks}
                selectedTaskId={selectedTaskId}
                showCreatedBy={canSeeAll}
                userNames={userNames}
                onSelectTask={handleSelectTask}
                onRevoke={(id) => revokeMutation.mutate(id)}
              />
            </div>
          )}
        </div>
        {selectedTaskId && (
          <div>
            <TaskDetail taskId={selectedTaskId} isRunning={selectedTask?.status === "Started" || selectedTask?.status === "Pending"} />
          </div>
        )}
      </div>
    </div>
  );
}

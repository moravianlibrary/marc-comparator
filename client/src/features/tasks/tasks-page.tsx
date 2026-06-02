import { useMemo, useState, useSyncExternalStore } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import { Button } from "@/components/ui/button";
import type { Task } from "@/types/task";
import type { User } from "@/types/user";
import { TaskTable } from "./task-table";
import { TaskDetail } from "./task-detail";
import { SkeletonTable } from "@/components/skeletons/skeleton-table";

const XL_QUERY = "(min-width: 1280px)";
function useIsXl() {
  return useSyncExternalStore(
    (cb) => {
      const mql = window.matchMedia(XL_QUERY);
      mql.addEventListener("change", cb);
      return () => mql.removeEventListener("change", cb);
    },
    () => window.matchMedia(XL_QUERY).matches,
  );
}

export function TasksPage() {
  const { t } = useTranslation("tasks");
  const queryClient = useQueryClient();
  const { hasPermission } = useHasPermission();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTaskId = searchParams.get("taskId");
  const isXl = useIsXl();
  const pageSize = isXl ? 20 : 15;
  const [page, setPage] = useState(1);

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
    queryKey: ["tasks", "list", searchEndpoint, page],
    queryFn: () =>
      apiClient.post(searchEndpoint, { page, page_size: pageSize }).then((r) => r.data),
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
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);
  const selectedTask = selectedTaskId ? tasks.find((t) => t.task_id === selectedTaskId) : undefined;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>

      <div
        className={`grid gap-4 ${selectedTaskId ? "grid-cols-1 xl:grid-cols-[1fr_1fr]" : "grid-cols-1"}`}
      >
        <div className="space-y-4">
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
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {t("common:pagination.page", { page, total: totalPages })}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                >
                  {t("common:pagination.previous")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                >
                  {t("common:pagination.next")}
                </Button>
              </div>
            </div>
          )}
        </div>
        {selectedTaskId && (
          <div className="xl:sticky xl:top-20 xl:self-start">
            <TaskDetail
              taskId={selectedTaskId}
              isRunning={selectedTask?.status === "Started" || selectedTask?.status === "Pending"}
              progress={selectedTask?.progress}
            />
          </div>
        )}
      </div>
    </div>
  );
}

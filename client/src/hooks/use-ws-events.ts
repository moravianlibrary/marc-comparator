import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { wsClient } from "@/lib/ws-client";
import { addNotification } from "@/layout/toast-history";

interface TaskStatusMessage {
  task_id: string;
  task_type?: string;
  name?: string;
  status: "Pending" | "Started" | "Success" | "Failure";
}

const COALESCE_MS = 300;

export function useWsEvents() {
  const { t } = useTranslation("tasks");
  const queryClient = useQueryClient();

  const tRef = useRef(t);
  tRef.current = t;

  useEffect(() => {
    wsClient.connect();

    const pendingEvents = new Map<string, { data: TaskStatusMessage; timerId: ReturnType<typeof setTimeout> }>();

    function handleTaskStatus(data: TaskStatusMessage) {
      const t = tRef.current;
      queryClient.invalidateQueries({ queryKey: ["tasks"] });

      const taskName = data.task_type
        ? t(`type.${data.task_type}`, { defaultValue: data.task_type })
        : data.task_id;

      if (data.status === "Pending") {
        toast.info(t("toast.pending", { name: taskName }));
        addNotification({
          title: taskName ?? data.task_id,
          description: t("toast.pending", { name: taskName }),
          variant: "default",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
      } else if (data.status === "Started") {
        toast.info(t("toast.started", { name: taskName }));
        addNotification({
          title: taskName ?? data.task_id,
          description: t("toast.started", { name: taskName }),
          variant: "default",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
      } else if (data.status === "Success") {
        toast.success(t("toast.completed", { name: taskName }));
        addNotification({
          title: taskName ?? data.task_id,
          description: t("toast.completed", { name: taskName }),
          variant: "success",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
        queryClient.invalidateQueries({ queryKey: ["catalog-records"] });
      } else if (data.status === "Failure") {
        toast.error(t("toast.failed", { name: taskName }));
        addNotification({
          title: taskName ?? data.task_id,
          description: t("toast.failed", { name: taskName }),
          variant: "error",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
        queryClient.invalidateQueries({ queryKey: ["catalog-records"] });
      }
    }

    const unsubStatus = wsClient.on("task_status", (raw) => {
      const data = raw as TaskStatusMessage;
      const taskId = data.task_id;

      // Cancel any pending coalesced event for this task
      const existing = pendingEvents.get(taskId);
      if (existing) {
        clearTimeout(existing.timerId);
      }

      // Schedule the event to fire after COALESCE_MS
      const timerId = setTimeout(() => {
        pendingEvents.delete(taskId);
        handleTaskStatus(data);
      }, COALESCE_MS);

      pendingEvents.set(taskId, { data, timerId });
    });

    const unsubProgress = wsClient.on("task_progress", (raw) => {
      const data = raw as { task_id: string; progress: number | null };
      const updateItems = (old: { items: { task_id: string; progress: number | null }[] } | undefined) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((t) =>
            t.task_id === data.task_id ? { ...t, progress: data.progress } : t,
          ),
        };
      };
      queryClient.setQueriesData<{ items: { task_id: string; progress: number | null }[] }>({ queryKey: ["tasks", "running"] }, updateItems);
      queryClient.setQueriesData<{ items: { task_id: string; progress: number | null }[] }>({ queryKey: ["tasks", "list"] }, updateItems);
    });

    const unsubLock = wsClient.on("lock_acquired", () => {
      queryClient.invalidateQueries({ queryKey: ["system", "locks"] });
    });

    const unsubUnlock = wsClient.on("lock_released", () => {
      queryClient.invalidateQueries({ queryKey: ["system", "locks"] });
    });

    return () => {
      // Clear all pending coalesced events on unmount
      for (const { timerId } of pendingEvents.values()) {
        clearTimeout(timerId);
      }
      pendingEvents.clear();
      unsubStatus();
      unsubProgress();
      unsubLock();
      unsubUnlock();
      wsClient.disconnect();
    };
  }, [queryClient]);
}

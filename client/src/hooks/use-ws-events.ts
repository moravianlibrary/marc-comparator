import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { wsClient } from "@/lib/ws-client";
import { addNotification } from "@/layout/toast-history";

export function useWsEvents() {
  const { t } = useTranslation("tasks");
  const queryClient = useQueryClient();

  useEffect(() => {
    wsClient.connect();

    const unsubStatus = wsClient.on("task_status", (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });

      const taskName = data.task_type ? t(`type.${data.task_type}`, { defaultValue: data.name }) : data.name;
      if (data.status === "Started") {
        toast.info(t("toast.started", { name: taskName }));
        addNotification({
          title: taskName,
          description: t("toast.started", { name: taskName }),
          variant: "default",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
      } else if (data.status === "Success") {
        toast.success(t("toast.completed", { name: taskName }));
        addNotification({
          title: taskName,
          description: t("toast.completed", { name: taskName }),
          variant: "success",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
        queryClient.invalidateQueries({ queryKey: ["catalog-records"] });
      } else if (data.status === "Failure") {
        toast.error(t("toast.failed", { name: taskName }));
        addNotification({
          title: taskName,
          description: t("toast.failed", { name: taskName }),
          variant: "error",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
        queryClient.invalidateQueries({ queryKey: ["catalog-records"] });
      }
    });

    const unsubProgress = wsClient.on("task_progress", () => {
      queryClient.invalidateQueries({ queryKey: ["tasks", "running"] });
    });

    const unsubLock = wsClient.on("lock_acquired", () => {
      queryClient.invalidateQueries({ queryKey: ["system", "locks"] });
    });

    const unsubUnlock = wsClient.on("lock_released", () => {
      queryClient.invalidateQueries({ queryKey: ["system", "locks"] });
    });

    return () => {
      unsubStatus();
      unsubProgress();
      unsubLock();
      unsubUnlock();
      wsClient.disconnect();
    };
  }, [queryClient, t]);
}

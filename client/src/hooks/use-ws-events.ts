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

      if (data.status === "Started") {
        toast.info(t("toast.started", { name: data.name }));
        addNotification({
          title: data.name,
          description: t("toast.started", { name: data.name }),
          variant: "default",
          timestamp: new Date().toISOString(),
        });
      } else if (data.status === "Success") {
        toast.success(t("toast.completed", { name: data.name }));
        addNotification({
          title: data.name,
          description: t("toast.completed", { name: data.name }),
          variant: "success",
          timestamp: new Date().toISOString(),
        });
      } else if (data.status === "Failure") {
        toast.error(t("toast.failed", { name: data.name }));
        addNotification({
          title: data.name,
          description: t("toast.failed", { name: data.name }),
          variant: "error",
          timestamp: new Date().toISOString(),
        });
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

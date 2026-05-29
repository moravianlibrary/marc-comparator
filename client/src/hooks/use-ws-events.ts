import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { wsClient } from "@/lib/ws-client";
import { addNotification } from "@/layout/toast-history";

interface TaskStatusMessage {
  task_id: string;
  task_type?: string;
  status: "Started" | "Success" | "Failure";
}

export function useWsEvents() {
  const { t } = useTranslation("tasks");
  const queryClient = useQueryClient();

  const tRef = useRef(t);
  tRef.current = t;

  useEffect(() => {
    wsClient.connect();

    const unsubStatus = wsClient.on("task_status", (raw) => {
      const data = raw as TaskStatusMessage;
      queryClient.invalidateQueries({ queryKey: ["tasks"] });

      const taskName = data.task_type ? tRef.current(`type.${data.task_type}`, { defaultValue: data.task_type }) : data.task_type;
      if (data.status === "Started") {
        toast.info(tRef.current("toast.started", { name: taskName }));
        addNotification({
          title: taskName,
          description: tRef.current("toast.started", { name: taskName }),
          variant: "default",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
      } else if (data.status === "Success") {
        toast.success(tRef.current("toast.completed", { name: taskName }));
        addNotification({
          title: taskName,
          description: tRef.current("toast.completed", { name: taskName }),
          variant: "success",
          timestamp: new Date().toISOString(),
          taskId: data.task_id,
        });
        queryClient.invalidateQueries({ queryKey: ["catalog-records"] });
      } else if (data.status === "Failure") {
        toast.error(tRef.current("toast.failed", { name: taskName }));
        addNotification({
          title: taskName,
          description: tRef.current("toast.failed", { name: taskName }),
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
  }, [queryClient]);
}

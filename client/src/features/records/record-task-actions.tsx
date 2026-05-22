import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { MoreHorizontal } from "lucide-react";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { RecordFilter } from "./types";
import type { ProcessRecordsSettings } from "@/types/settings";

type TaskAction =
  | "process"
  | "link-authorities"
  | "compare"
  | "validate";

interface RecordTaskActionsProps {
  filters: RecordFilter;
}

export function RecordTaskActions({ filters }: RecordTaskActionsProps) {
  const { t } = useTranslation("records");
  const queryClient = useQueryClient();
  const [pendingAction, setPendingAction] = useState<TaskAction | null>(null);

  const { data: processSettings } = useQuery<ProcessRecordsSettings>({
    queryKey: ["settings", "process-records"],
    queryFn: () =>
      apiClient
        .get<ProcessRecordsSettings>("/settings/record-tools/process-records")
        .then((r) => r.data),
  });

  const onTaskCreated = () =>
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const onError = () => toast.error(t("common:error"));

  const processMutation = useMutation({
    mutationFn: () => apiClient.post("/catalog-records/process", filters),
    onSuccess: onTaskCreated,
    onError,
  });

  const linkAuthoritiesMutation = useMutation({
    mutationFn: async () => {
      if (!processSettings) return;
      for (const targetBase of processSettings.target_bases) {
        await apiClient.post("/authority-linking/task", {
          linkers: processSettings.authority_linkers,
          target_base: targetBase,
          filters,
        });
      }
    },
    onSuccess: onTaskCreated,
    onError,
  });

  const compareMutation = useMutation({
    mutationFn: async () => {
      if (!processSettings) return;
      for (const targetBase of processSettings.target_bases) {
        await apiClient.post("/comparison/task", {
          target_base: targetBase,
          filters,
        });
      }
    },
    onSuccess: onTaskCreated,
    onError,
  });

  const validateMutation = useMutation({
    mutationFn: () => {
      if (!processSettings) return Promise.resolve();
      return apiClient.post("/validation/task", {
        validators: processSettings.validators,
        filters,
      });
    },
    onSuccess: onTaskCreated,
    onError,
  });

  function confirmAction() {
    if (!pendingAction) return;
    switch (pendingAction) {
      case "process":
        processMutation.mutate();
        break;
      case "link-authorities":
        linkAuthoritiesMutation.mutate();
        break;
      case "compare":
        compareMutation.mutate();
        break;
      case "validate":
        validateMutation.mutate();
        break;
    }
    setPendingAction(null);
  }

  const actionLabel: Record<TaskAction, string> = {
    process: t("table.actions.process"),
    "link-authorities": t("table.actions.link-authorities"),
    compare: t("table.actions.compare"),
    validate: t("table.actions.validate"),
  };

  const isBusy =
    processMutation.isPending ||
    linkAuthoritiesMutation.isPending ||
    compareMutation.isPending ||
    validateMutation.isPending;

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setPendingAction("process")}
        disabled={isBusy}
      >
        {t("table.actions.process")}
      </Button>

      <AlertDialog
        open={pendingAction !== null}
        onOpenChange={(open) => !open && setPendingAction(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("common:confirm")}</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingAction &&
                t("table.actions.confirm-task", {
                  action: actionLabel[pendingAction],
                })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmAction}>
              {t("common:confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

interface AdvancedTaskActionsProps {
  filters: RecordFilter;
}

export function AdvancedTaskActions({ filters }: AdvancedTaskActionsProps) {
  const { t } = useTranslation("records");
  const queryClient = useQueryClient();
  const [pendingAction, setPendingAction] = useState<TaskAction | null>(null);

  const { data: processSettings } = useQuery<ProcessRecordsSettings>({
    queryKey: ["settings", "process-records"],
    queryFn: () =>
      apiClient
        .get<ProcessRecordsSettings>("/settings/record-tools/process-records")
        .then((r) => r.data),
  });

  const onTaskCreated = () =>
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const onError = () => toast.error(t("common:error"));

  const linkAuthoritiesMutation = useMutation({
    mutationFn: async () => {
      if (!processSettings) return;
      for (const targetBase of processSettings.target_bases) {
        await apiClient.post("/authority-linking/task", {
          linkers: processSettings.authority_linkers,
          target_base: targetBase,
          filters,
        });
      }
    },
    onSuccess: onTaskCreated,
    onError,
  });

  const compareMutation = useMutation({
    mutationFn: async () => {
      if (!processSettings) return;
      for (const targetBase of processSettings.target_bases) {
        await apiClient.post("/comparison/task", {
          target_base: targetBase,
          filters,
        });
      }
    },
    onSuccess: onTaskCreated,
    onError,
  });

  const validateMutation = useMutation({
    mutationFn: () => {
      if (!processSettings) return Promise.resolve();
      return apiClient.post("/validation/task", {
        validators: processSettings.validators,
        filters,
      });
    },
    onSuccess: onTaskCreated,
    onError,
  });

  function confirmAction() {
    if (!pendingAction) return;
    switch (pendingAction) {
      case "link-authorities":
        linkAuthoritiesMutation.mutate();
        break;
      case "compare":
        compareMutation.mutate();
        break;
      case "validate":
        validateMutation.mutate();
        break;
    }
    setPendingAction(null);
  }

  const actionLabel: Record<string, string> = {
    "link-authorities": t("table.actions.link-authorities"),
    compare: t("table.actions.compare"),
    validate: t("table.actions.validate"),
  };

  const isBusy =
    linkAuthoritiesMutation.isPending ||
    compareMutation.isPending ||
    validateMutation.isPending;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            disabled={isBusy}
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onSelect={() => setPendingAction("link-authorities")}
          >
            {t("table.actions.link-authorities")}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setPendingAction("compare")}>
            {t("table.actions.compare")}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setPendingAction("validate")}>
            {t("table.actions.validate")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog
        open={pendingAction !== null}
        onOpenChange={(open) => !open && setPendingAction(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("common:confirm")}</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingAction &&
                t("table.actions.confirm-task", {
                  action: actionLabel[pendingAction],
                })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmAction}>
              {t("common:confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

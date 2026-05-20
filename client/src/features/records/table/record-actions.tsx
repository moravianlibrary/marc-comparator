import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { MoreHorizontal } from "lucide-react";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { RecordSummary } from "../types";

interface RecordActionsProps {
  record: RecordSummary;
}

export function RecordActions({ record }: RecordActionsProps) {
  const { t } = useTranslation("records");
  const queryClient = useQueryClient();

  const processMutation = useMutation({
    mutationFn: () =>
      apiClient.post("/catalog-records/process", {
        bases: [record.base],
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    onError: () => toast.error(t("common:error")),
  });

  const visibilityMutation = useMutation({
    mutationFn: (visible: boolean) =>
      apiClient.post("/catalog-records/visibility", {
        filters: { bases: [record.base] },
        visible,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["catalog-records"] }),
    onError: () => toast.error(t("common:error")),
  });

  const isHidden = record.state.includes("Hidden");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => processMutation.mutate()}>
          {t("table.actions.process")}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => visibilityMutation.mutate(!isHidden)}
        >
          {isHidden ? t("table.actions.show") : t("table.actions.hide")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

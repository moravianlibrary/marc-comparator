import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { MoreHorizontal } from "lucide-react";
import apiClient from "@/lib/api-client";
import { useSystemInfo } from "@/hooks/use-system-info";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { RecordFilter } from "./types";
import type { ProcessRecordsSettings } from "@/types/settings";

type SimpleAction = "process" | "compare";
type DialogAction = "link-authorities" | "validate";

interface RecordTaskActionsProps {
  filters: RecordFilter;
  totalCount?: number;
}

export function RecordTaskActions({ filters, totalCount }: RecordTaskActionsProps) {
  const { t } = useTranslation("records");
  const queryClient = useQueryClient();
  const [pendingAction, setPendingAction] = useState<SimpleAction | null>(null);

  const onTaskCreated = () =>
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const onError = () => toast.error(t("common:error"));

  const processMutation = useMutation({
    mutationFn: () => apiClient.post("/catalog-records/process", filters),
    onSuccess: onTaskCreated,
    onError,
  });

  function confirmAction() {
    if (!pendingAction) return;
    if (pendingAction === "process") processMutation.mutate();
    setPendingAction(null);
  }

  const isSingle = totalCount === 1;

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setPendingAction("process")}
        disabled={processMutation.isPending}
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
              {pendingAction && (isSingle
                ? t("table.actions.confirm-task-single", {
                    action: t(`table.actions.${pendingAction}`),
                  })
                : t("table.actions.confirm-task-bulk", {
                    action: t(`table.actions.${pendingAction}`),
                    count: totalCount ?? "?",
                  }))}
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
  totalCount?: number;
}

export function AdvancedTaskActions({ filters, totalCount }: AdvancedTaskActionsProps) {
  const { t } = useTranslation("records");
  const queryClient = useQueryClient();
  const [pendingSimple, setPendingSimple] = useState<SimpleAction | null>(null);
  const [pendingDialog, setPendingDialog] = useState<DialogAction | null>(null);

  // -- Authority linking dialog state --
  const [selectedBase, setSelectedBase] = useState<string | null>(null);
  const [selectedLinkers, setSelectedLinkers] = useState<Set<string>>(new Set());

  // -- Validation dialog state --
  const [selectedValidators, setSelectedValidators] = useState<Set<string>>(new Set());

  const { data: systemInfo } = useSystemInfo();

  const { data: processSettings } = useQuery<ProcessRecordsSettings>({
    queryKey: ["settings", "process-records"],
    queryFn: () =>
      apiClient
        .get<ProcessRecordsSettings>("/settings/record-tools/process-records")
        .then((r) => r.data),
  });

  const authorityLinkers = systemInfo?.enabled_authority_linkers ?? [];
  const enabledValidators = systemInfo?.enabled_validators ?? [];

  const onTaskCreated = () =>
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const onError = () => toast.error(t("common:error"));

  const linkAuthoritiesMutation = useMutation({
    mutationFn: async ({ base, linkers }: { base: string; linkers: string[] }) => {
      await apiClient.post("/authority-linking/task", {
        linkers,
        target_base: base,
        filters,
      });
    },
    onSuccess: onTaskCreated,
    onError,
  });

  const compareMutation = useMutation({
    mutationFn: async () => {
      if (!processSettings) return;
      await Promise.all(
        processSettings.target_bases.map((targetBase) =>
          apiClient.post("/comparison/task", {
            target_base: targetBase,
            filters,
          }),
        ),
      );
    },
    onSuccess: onTaskCreated,
    onError,
  });

  const validateMutation = useMutation({
    mutationFn: async (validators: string[]) => {
      await apiClient.post("/validation/task", { validators, filters });
    },
    onSuccess: onTaskCreated,
    onError,
  });

  function confirmSimple() {
    if (pendingSimple === "compare") compareMutation.mutate();
    setPendingSimple(null);
  }

  function openLinkAuthorities() {
    const bases = [...new Set(authorityLinkers.flatMap((l) => l.target_bases))];
    const defaultBase = bases.length === 1 ? bases[0] : null;
    setSelectedBase(defaultBase);
    // If only one base, pre-select all compatible linkers if there's exactly one
    const compatible = defaultBase
      ? authorityLinkers.filter((l) => l.target_bases.includes(defaultBase))
      : [];
    setSelectedLinkers(
      compatible.length === 1 ? new Set([compatible[0].name]) : new Set(),
    );
    setPendingDialog("link-authorities");
  }

  function openValidate() {
    setSelectedValidators(
      enabledValidators.length === 1
        ? new Set([enabledValidators[0]])
        : new Set(),
    );
    setPendingDialog("validate");
  }

  function confirmLinkAuthorities() {
    if (!selectedBase || selectedLinkers.size === 0) return;
    linkAuthoritiesMutation.mutate({
      base: selectedBase,
      linkers: Array.from(selectedLinkers),
    });
    setPendingDialog(null);
  }

  function confirmValidate() {
    if (selectedValidators.size === 0) return;
    validateMutation.mutate(Array.from(selectedValidators));
    setPendingDialog(null);
  }

  const availableBases = [
    ...new Set(authorityLinkers.flatMap((l) => l.target_bases)),
  ];

  const linkerOptions = authorityLinkers.map((linker) => ({
    id: linker.name,
    label: linker.name,
    disabled: !linker.target_bases.includes(selectedBase || ""),
  }));

  const isSingle = totalCount === 1;
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
          <DropdownMenuItem onSelect={openLinkAuthorities}>
            {t("table.actions.link-authorities")}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setPendingSimple("compare")}>
            {t("table.actions.compare")}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={openValidate}>
            {t("table.actions.validate")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Simple confirm for compare */}
      <AlertDialog
        open={pendingSimple !== null}
        onOpenChange={(open) => !open && setPendingSimple(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("common:confirm")}</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingSimple && (isSingle
                ? t("table.actions.confirm-task-single", {
                    action: t(`table.actions.${pendingSimple}`),
                  })
                : t("table.actions.confirm-task-bulk", {
                    action: t(`table.actions.${pendingSimple}`),
                    count: totalCount ?? "?",
                  }))}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmSimple}>
              {t("common:confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Authority Linking dialog */}
      <Dialog
        open={pendingDialog === "link-authorities"}
        onOpenChange={(open) => !open && setPendingDialog(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("table.actions.authority-linking-title")}
            </DialogTitle>
            <DialogDescription>
              {isSingle
                ? t("table.actions.authority-linking-description-single")
                : t("table.actions.authority-linking-description-bulk", { count: totalCount ?? "?" })}
            </DialogDescription>
          </DialogHeader>

          {authorityLinkers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("table.actions.no-linkers")}
            </p>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>{t("table.actions.select-base")}</Label>
                <Select
                  value={selectedBase ?? ""}
                  onValueChange={(v) => {
                    setSelectedBase(v);
                    const compatible = authorityLinkers.filter((l) =>
                      l.target_bases.includes(v),
                    );
                    setSelectedLinkers(
                      compatible.length === 1
                        ? new Set([compatible[0].name])
                        : new Set(),
                    );
                  }}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={t("table.actions.select-base-placeholder")}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {availableBases.map((base) => (
                      <SelectItem key={base} value={base}>
                        {base}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>{t("table.actions.select-linkers")}</Label>
                <div className="space-y-2">
                  {linkerOptions.map((opt) => (
                    <div key={opt.id} className="flex items-center gap-2">
                      <Checkbox
                        id={`linker-${opt.id}`}
                        disabled={opt.disabled}
                        checked={selectedLinkers.has(opt.id)}
                        onCheckedChange={(checked) => {
                          setSelectedLinkers((prev) => {
                            const next = new Set(prev);
                            if (checked) next.add(opt.id);
                            else next.delete(opt.id);
                            return next;
                          });
                        }}
                      />
                      <Label
                        htmlFor={`linker-${opt.id}`}
                        className={opt.disabled ? "text-muted-foreground" : ""}
                      >
                        {opt.label}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDialog(null)}>
              {t("common:cancel")}
            </Button>
            <Button
              onClick={confirmLinkAuthorities}
              disabled={
                !selectedBase ||
                selectedLinkers.size === 0 ||
                authorityLinkers.length === 0
              }
            >
              {t("common:confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Validation dialog */}
      <Dialog
        open={pendingDialog === "validate"}
        onOpenChange={(open) => !open && setPendingDialog(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("table.actions.validate-title")}</DialogTitle>
            <DialogDescription>
              {isSingle
                ? t("table.actions.validate-description-single")
                : t("table.actions.validate-description-bulk", { count: totalCount ?? "?" })}
            </DialogDescription>
          </DialogHeader>

          {enabledValidators.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("table.actions.no-validators")}
            </p>
          ) : (
            <div className="space-y-2">
              <Label>{t("table.actions.select-validators")}</Label>
              <div className="space-y-2">
                {enabledValidators.map((v) => (
                  <div key={v} className="flex items-center gap-2">
                    <Checkbox
                      id={`validator-${v}`}
                      checked={selectedValidators.has(v)}
                      onCheckedChange={(checked) => {
                        setSelectedValidators((prev) => {
                          const next = new Set(prev);
                          if (checked) next.add(v);
                          else next.delete(v);
                          return next;
                        });
                      }}
                    />
                    <Label htmlFor={`validator-${v}`}>{t(`validator-name.${v}`, { defaultValue: v })}</Label>
                  </div>
                ))}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDialog(null)}>
              {t("common:cancel")}
            </Button>
            <Button
              onClick={confirmValidate}
              disabled={
                selectedValidators.size === 0 ||
                enabledValidators.length === 0
              }
            >
              {t("common:confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

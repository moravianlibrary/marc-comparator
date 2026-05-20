import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import type { SettingsScope } from "@/types/settings";
import { CatalogSettingsForm } from "./catalog-settings-form";
import { TaskSettingsForm } from "./task-settings-form";
import { AuthorityLinkingSettingsForm } from "./authority-linking-settings-form";
import { ComparisonSettingsForm } from "./comparison-settings-form";
import { ValidationSettingsForm } from "./validation-settings-form";
import { ProcessRecordsSettingsForm } from "./process-records-settings-form";

const SETTINGS_SCOPES: SettingsScope[] = [
  "catalog",
  "tasks",
  "authority-linkers",
  "comparators",
  "validators",
  "process-records",
];

const SETTINGS_ENDPOINTS: Record<SettingsScope, string> = {
  catalog: "/settings/system/catalog",
  tasks: "/settings/system/tasks",
  "authority-linkers": "/settings/record-tools/authority-linkers",
  comparators: "/settings/record-tools/comparators",
  validators: "/settings/record-tools/validators",
  "process-records": "/settings/record-tools/process-records",
};

export function SettingsPage() {
  const { t } = useTranslation("settings");
  const queryClient = useQueryClient();

  const [activeScope, setActiveScope] = useState<SettingsScope>("catalog");
  const [isDirty, setIsDirty] = useState(false);
  const [pendingScope, setPendingScope] = useState<SettingsScope | null>(null);
  const [formRef, setFormRef] = useState<{
    submit: () => void;
    reset: () => void;
  } | null>(null);

  const endpoint = SETTINGS_ENDPOINTS[activeScope];

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings", activeScope],
    queryFn: () => apiClient.get(endpoint).then((r) => r.data),
  });

  const saveMutation = useMutation({
    mutationFn: (data: unknown) => apiClient.post(endpoint, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", activeScope] });
      setIsDirty(false);
      toast.success(t("common:save") + " ✓");
    },
  });

  const handleScopeChange = useCallback(
    (newScope: SettingsScope) => {
      if (isDirty) {
        setPendingScope(newScope);
      } else {
        setActiveScope(newScope);
      }
    },
    [isDirty]
  );

  const handleDiscardAndSwitch = useCallback(() => {
    if (pendingScope) {
      formRef?.reset();
      setIsDirty(false);
      setActiveScope(pendingScope);
      setPendingScope(null);
    }
  }, [pendingScope, formRef]);

  function renderForm() {
    if (isLoading || !settings) return null;

    const commonProps = {
      data: settings,
      onDirtyChange: setIsDirty,
      onFormRef: setFormRef,
      onSubmit: (data: unknown) => saveMutation.mutate(data),
    };

    switch (activeScope) {
      case "catalog":
        return <CatalogSettingsForm {...commonProps} />;
      case "tasks":
        return <TaskSettingsForm {...commonProps} />;
      case "authority-linkers":
        return <AuthorityLinkingSettingsForm {...commonProps} />;
      case "comparators":
        return <ComparisonSettingsForm {...commonProps} />;
      case "validators":
        return <ValidationSettingsForm {...commonProps} />;
      case "process-records":
        return <ProcessRecordsSettingsForm {...commonProps} />;
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
      </div>

      <div className="flex items-center gap-4">
        <Select value={activeScope} onValueChange={handleScopeChange}>
          <SelectTrigger className="w-[320px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SETTINGS_SCOPES.map((scope) => (
              <SelectItem key={scope} value={scope}>
                {t(`types.${scope}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          onClick={() => formRef?.submit()}
          disabled={!isDirty || saveMutation.isPending}
        >
          {t("common:save")}
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            formRef?.reset();
            setIsDirty(false);
          }}
          disabled={!isDirty}
        >
          {t("common:discard")}
        </Button>
      </div>

      {renderForm()}

      <AlertDialog
        open={pendingScope !== null}
        onOpenChange={(open) => !open && setPendingScope(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("unsaved-warning")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("unsaved-warning")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDiscardAndSwitch}>
              {t("common:discard")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

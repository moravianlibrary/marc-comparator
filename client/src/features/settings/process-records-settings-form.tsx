import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import { processRecordsSettingsSchema, type ProcessRecordsSettingsFormValues } from "./schemas";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import type { ProcessRecordsSettings, SystemInfo } from "@/types/settings";

interface Props {
  data: ProcessRecordsSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: ProcessRecordsSettings) => void;
}

export function ProcessRecordsSettingsForm({
  data,
  onDirtyChange,
  onFormRef,
  onSubmit,
}: Props) {
  const { t } = useTranslation("settings");

  const { data: systemInfo } = useQuery<SystemInfo>({
    queryKey: ["system", "info"],
    queryFn: () => apiClient.get<SystemInfo>("/system/info").then((r) => r.data),
  });

  const form = useForm<ProcessRecordsSettingsFormValues>({
    resolver: zodResolver(processRecordsSettingsSchema),
    defaultValues: data,
  });

  useEffect(() => {
    onFormRef({
      submit: () => form.handleSubmit(onSubmit)(),
      reset: () => form.reset(data),
    });
  }, [form, onSubmit, data, onFormRef]);

  useEffect(() => {
    onDirtyChange(form.formState.isDirty);
  }, [form.formState.isDirty, onDirtyChange]);

  const linkerTargetBases = [
    ...new Set(
      systemInfo?.enabled_authority_linkers.flatMap((l) => l.target_bases) ?? [],
    ),
  ];

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="max-w-md space-y-4">
        <FormField
          control={form.control}
          name="target_bases"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("process-records.target-bases")}</FormLabel>
              <div className="space-y-2">
                {linkerTargetBases.map((base) => (
                  <label key={base} className="flex items-center gap-2">
                    <Checkbox
                      checked={field.value.includes(base)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          field.onChange([...field.value, base]);
                        } else {
                          field.onChange(field.value.filter((b) => b !== base));
                        }
                      }}
                    />
                    <span className="text-sm">{base}</span>
                  </label>
                ))}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="authority_linkers"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("process-records.authority-linkers")}</FormLabel>
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <Checkbox
                    checked={field.value.includes("knihovny-cz")}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        field.onChange([...field.value, "knihovny-cz"]);
                      } else {
                        field.onChange(field.value.filter((v) => v !== "knihovny-cz"));
                      }
                    }}
                  />
                  <span className="text-sm">Knihovny.cz</span>
                </label>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="validators"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("process-records.validators")}</FormLabel>
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <Checkbox
                    checked={field.value.includes("kramerius-links")}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        field.onChange([...field.value, "kramerius-links"]);
                      } else {
                        field.onChange(field.value.filter((v) => v !== "kramerius-links"));
                      }
                    }}
                  />
                  <span className="text-sm">Kramerius Links</span>
                </label>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
}

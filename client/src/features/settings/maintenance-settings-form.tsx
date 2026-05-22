import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { maintenanceSettingsSchema, type MaintenanceSettingsFormValues } from "./schemas";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormDescription,
  FormMessage,
} from "@/components/ui/form";
import type { MaintenanceSettings } from "@/types/settings";

interface Props {
  data: MaintenanceSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: MaintenanceSettings) => void;
}

export function MaintenanceSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation("settings");

  const form = useForm<MaintenanceSettingsFormValues>({
    resolver: zodResolver(maintenanceSettingsSchema),
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

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="max-w-md space-y-6">
        <div className="space-y-4">
          <h3 className="text-sm font-medium">{t("maintenance.task-cleanup.title")}</h3>

          <FormField
            control={form.control}
            name="task_cleanup.enabled"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3">
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel className="!mt-0">{t("maintenance.enabled")}</FormLabel>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="task_cleanup.interval_hours"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("maintenance.interval-hours")}</FormLabel>
                <FormDescription>{t("maintenance.interval-hours-description")}</FormDescription>
                <FormControl>
                  <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="task_cleanup_max_age_days"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("maintenance.max-age-days")}</FormLabel>
                <FormDescription>{t("maintenance.max-age-days-description")}</FormDescription>
                <FormControl>
                  <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="space-y-4">
          <h3 className="text-sm font-medium">{t("maintenance.sector-compaction.title")}</h3>

          <FormField
            control={form.control}
            name="sector_compaction.enabled"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3">
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel className="!mt-0">{t("maintenance.enabled")}</FormLabel>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="sector_compaction.interval_hours"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("maintenance.interval-hours")}</FormLabel>
                <FormDescription>{t("maintenance.interval-hours-description")}</FormDescription>
                <FormControl>
                  <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </form>
    </Form>
  );
}

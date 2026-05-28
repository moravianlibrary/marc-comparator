import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { taskSettingsSchema, type TaskSettingsFormValues } from "./schemas";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormDescription,
  FormMessage,
} from "@/components/ui/form";
import { HelpDialog } from "./help-dialog";
import { TasksHelp } from "./help-content";
import type { TaskSettings } from "@/types/settings";

interface Props {
  data: TaskSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: TaskSettings) => void;
}

export function TaskSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation("settings");

  const form = useForm<TaskSettingsFormValues>({
    resolver: zodResolver(taskSettingsSchema),
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
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t("types.tasks")}</CardTitle>
            <HelpDialog titleKey="types.tasks"><TasksHelp /></HelpDialog>
          </CardHeader>
          <CardContent className="max-w-md space-y-4">
            <FormField
              control={form.control}
              name="progress_update_interval"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("tasks-settings.progress-update-interval")}</FormLabel>
                  <FormDescription>{t("tasks-settings.progress-update-interval-description")}</FormDescription>
                  <FormControl>
                    <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="commit_interval"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("tasks-settings.commit-interval")}</FormLabel>
                  <FormDescription>{t("tasks-settings.commit-interval-description")}</FormDescription>
                  <FormControl>
                    <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="analytics_rebuild_interval"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("tasks-settings.analytics-rebuild-interval")}</FormLabel>
                  <FormDescription>{t("tasks-settings.analytics-rebuild-interval-description")}</FormDescription>
                  <FormControl>
                    <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}

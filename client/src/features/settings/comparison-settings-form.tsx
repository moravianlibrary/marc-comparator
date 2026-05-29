import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { comparisonSettingsSchema, type ComparisonSettingsFormValues } from "./schemas";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { HelpDialog } from "./help-dialog";
import { ComparatorsHelp } from "./help-content";
import type { ComparisonSettings } from "@/types/settings";

interface Props {
  data: ComparisonSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: ComparisonSettings) => void;
}

export function ComparisonSettingsForm({
  data,
  onDirtyChange,
  onFormRef,
  onSubmit,
}: Props) {
  const { t } = useTranslation("settings");

  const defaultValues = useMemo<ComparisonSettingsFormValues>(() => ({
    comparator: data.comparator ?? {
      ollama_url: "http://localhost:11434",
      llm_enabled: false,
      nonstandard_llm_enabled: false,
      valid_threshold: 6,
      warning_threshold: 12,
    },
  }), [data]);

  const form = useForm<ComparisonSettingsFormValues>({
    resolver: zodResolver(comparisonSettingsSchema),
    defaultValues,
  });

  useEffect(() => {
    onFormRef({
      submit: () => form.handleSubmit(onSubmit)(),
      reset: () => form.reset(defaultValues),
    });
  }, [form, onSubmit, defaultValues, onFormRef]);

  useEffect(() => {
    onDirtyChange(form.formState.isDirty);
  }, [form.formState.isDirty, onDirtyChange]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t("comparator.title")}</CardTitle>
            <HelpDialog titleKey="comparators.comparator.title"><ComparatorsHelp /></HelpDialog>
          </CardHeader>
          <CardContent className="max-w-xl space-y-4">
            <FormField
              control={form.control}
              name="comparator.ollama_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("comparator.ollama-url")}</FormLabel>
                  <FormControl><Input {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="comparator.llm_enabled"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <FormLabel>{t("comparator.llm-enabled")}</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="comparator.nonstandard_llm_enabled"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <FormLabel>{t("comparator.nonstandard-llm-enabled")}</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="comparator.valid_threshold"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("comparator.valid-threshold")}</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="comparator.warning_threshold"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("comparator.warning-threshold")}</FormLabel>
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

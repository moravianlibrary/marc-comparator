import { useEffect } from "react";
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

  const defaultValues: ComparisonSettingsFormValues = {
    intiim: data.intiim ?? {
      ollama_url: "http://localhost:11434",
      llm_enabled: false,
      nonstandard_llm_enabled: false,
      valid_threshold: 6,
      warning_threshold: 12,
    },
  };

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
          <CardHeader>
            <CardTitle className="text-base">{t("comparators.intiim.title")}</CardTitle>
          </CardHeader>
          <CardContent className="max-w-md space-y-4">
            <FormField
              control={form.control}
              name="intiim.ollama_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("comparators.intiim.ollama-url")}</FormLabel>
                  <FormControl><Input {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="intiim.llm_enabled"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <FormLabel>{t("comparators.intiim.llm-enabled")}</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="intiim.nonstandard_llm_enabled"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <FormLabel>{t("comparators.intiim.nonstandard-llm-enabled")}</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="intiim.valid_threshold"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("comparators.intiim.valid-threshold")}</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="intiim.warning_threshold"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("comparators.intiim.warning-threshold")}</FormLabel>
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

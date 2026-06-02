import { useFieldArray } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useSettingsForm } from "./use-settings-form";
import { Plus, Trash2 } from "lucide-react";
import { catalogSettingsSchema, type CatalogSettingsFormValues } from "./schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { CatalogHelp } from "./help-content";
import type { CatalogSettings } from "@/types/settings";

interface Props {
  data: CatalogSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: CatalogSettings) => void;
}

export function CatalogSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation("settings");

  const form = useSettingsForm({
    schema: catalogSettingsSchema,
    defaultValues: data,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "clients",
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t("catalog.clients")}</CardTitle>
            <HelpDialog titleKey="types.catalog">
              <CatalogHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent className="space-y-4">
            {fields.map((field, index) => (
              <Card key={field.id}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-base">
                    {form.watch(`clients.${index}.base`) || t("catalog.base")}
                  </CardTitle>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(index)}
                    disabled={fields.length <= 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name={`clients.${index}.base`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.base")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`clients.${index}.host`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.host")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`clients.${index}.endpoint`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.endpoint")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`clients.${index}.timeout`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.timeout")}</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            {...field}
                            onChange={(e) => field.onChange(Number(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`clients.${index}.total_retry`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.total-retry")}</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            {...field}
                            onChange={(e) => field.onChange(Number(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`clients.${index}.retry_backoff_factor`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.retry-backoff-factor")}</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            {...field}
                            onChange={(e) => field.onChange(Number(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`clients.${index}.system_number_pattern`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.system-number-pattern")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`clients.${index}.oai_identifier_template`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("catalog.oai-identifier-template")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                append({
                  base: "",
                  host: "",
                  endpoint: "OAI",
                  timeout: 30,
                  total_retry: 5,
                  retry_backoff_factor: 1,
                  system_number_pattern: "\\d{9}",
                  oai_sets: [],
                  oai_identifier_template: "",
                })
              }
            >
              <Plus className="mr-2 h-4 w-4" />
              {t("catalog.add-client")}
            </Button>
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}

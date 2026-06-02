import { useMemo } from "react";
import { useFieldArray } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useSettingsForm } from "./use-settings-form";
import { Plus, Trash2 } from "lucide-react";
import { authorityLinkingSettingsSchema, type AuthorityLinkingSettingsFormValues } from "./schemas";
import { Button } from "@/components/ui/button";
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
import { AuthorityLinkersHelp } from "./help-content";
import type { AuthorityLinkingSettings } from "@/types/settings";

interface Props {
  data: AuthorityLinkingSettings;
  onDirtyChange: (dirty: boolean) => void;
  onFormRef: (ref: { submit: () => void; reset: () => void }) => void;
  onSubmit: (data: AuthorityLinkingSettings) => void;
}

export function AuthorityLinkingSettingsForm({ data, onDirtyChange, onFormRef, onSubmit }: Props) {
  const { t } = useTranslation("settings");

  const defaultValues = useMemo<AuthorityLinkingSettingsFormValues>(
    () => ({
      "knihovny-cz": data["knihovny-cz"] ?? {
        api_url: "https://www.knihovny.cz/api/v1",
        mappings: [{ base: "", id_template: "", pattern: "", is_target: false }],
      },
    }),
    [data],
  );

  const form = useSettingsForm({
    schema: authorityLinkingSettingsSchema,
    defaultValues,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "knihovny-cz.mappings",
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t("authority-linkers.knihovny-cz.title")}</CardTitle>
            <HelpDialog titleKey="authority-linkers.knihovny-cz.title">
              <AuthorityLinkersHelp />
            </HelpDialog>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="knihovny-cz.api_url"
              render={({ field }) => (
                <FormItem className="max-w-md">
                  <FormLabel>{t("authority-linkers.knihovny-cz.api-url")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-2">
              <FormLabel>{t("authority-linkers.knihovny-cz.mappings")}</FormLabel>
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-end gap-2">
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.base`}
                    render={({ field }) => (
                      <FormItem className="flex-1">
                        <FormLabel className="text-xs">
                          {t("authority-linkers.knihovny-cz.mapping-base")}
                        </FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.id_template`}
                    render={({ field }) => (
                      <FormItem className="flex-1">
                        <FormLabel className="text-xs">
                          {t("authority-linkers.knihovny-cz.mapping-id-template")}
                        </FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.pattern`}
                    render={({ field }) => (
                      <FormItem className="flex-1">
                        <FormLabel className="text-xs">
                          {t("authority-linkers.knihovny-cz.mapping-pattern")}
                        </FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`knihovny-cz.mappings.${index}.is_target`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs">
                          {t("authority-linkers.knihovny-cz.mapping-is-target")}
                        </FormLabel>
                        <FormControl>
                          <div className="flex h-9 items-center">
                            <Switch checked={field.value} onCheckedChange={field.onChange} />
                          </div>
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(index)}
                    disabled={fields.length <= 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append({ base: "", id_template: "", pattern: "", is_target: false })}
              >
                <Plus className="mr-2 h-4 w-4" />
                {t("authority-linkers.knihovny-cz.add-mapping")}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}

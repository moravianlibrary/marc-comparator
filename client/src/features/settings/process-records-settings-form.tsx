import { useTranslation } from "react-i18next";
import { useSettingsForm } from "./use-settings-form";
import { useSystemInfo } from "@/hooks/use-system-info";
import { processRecordsSettingsSchema, type ProcessRecordsSettingsFormValues } from "./schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Checkbox } from "@/components/ui/checkbox";
import { HelpDialog } from "./help-dialog";
import { ProcessRecordsHelp } from "./help-content";
import type { ProcessRecordsSettings } from "@/types/settings";

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

  const { data: systemInfo } = useSystemInfo();

  const form = useSettingsForm({
    schema: processRecordsSettingsSchema,
    defaultValues: data,
    onFormRef,
    onDirtyChange,
    onSubmit,
  });

  const linkerTargetBases = [
    ...new Set(
      systemInfo?.enabled_authority_linkers.flatMap((l) => l.target_bases) ?? [],
    ),
  ];

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CardTitle className="text-base">{t("types.process-records")}</CardTitle>
            <HelpDialog titleKey="types.process-records"><ProcessRecordsHelp /></HelpDialog>
          </CardHeader>
          <CardContent className="max-w-md space-y-4">
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
          </CardContent>
        </Card>
      </form>
    </Form>
  );
}

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { useConfiguredBases } from "@/hooks/use-system-info";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

const schema = z.object({
  base: z.string().min(1),
  system_numbers_text: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

export function FetchBatchForm() {
  const { t } = useTranslation("records");

  const configuredBases = useConfiguredBases();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { base: "", system_numbers_text: "" },
  });

  useEffect(() => {
    if (configuredBases.length > 0 && !form.getValues("base")) {
      form.setValue("base", configuredBases[0]);
    }
  }, [configuredBases, form]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const systemNumbers = values.system_numbers_text
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);

      return apiClient.post("/catalog-records/fetch-batch", {
        per_base: [{ base: values.base, system_numbers: systemNumbers }],
      });
    },
    onSuccess: () => form.reset(),
    onError: () => toast.error(t("common:error")),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {t("addition.fetch-batch.title")}
        </CardTitle>
        <CardDescription>
          {t("addition.fetch-batch.description")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
            className="max-w-md space-y-4"
          >
            <FormField
              control={form.control}
              name="base"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("addition.fetch-batch.base")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {configuredBases.map((base) => (
                        <SelectItem key={base} value={base}>
                          {base}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="system_numbers_text"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {t("addition.fetch-batch.system-numbers")}
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      rows={8}
                      className="font-mono text-sm"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={mutation.isPending}>
              {t("addition.fetch-batch.submit")}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

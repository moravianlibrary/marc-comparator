import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { AxiosError } from "axios";
import apiClient from "@/lib/api-client";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SystemInfo } from "@/types/settings";

const schema = z.object({
  base: z.string().min(1),
  from_date: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export function SyncForm() {
  const { t } = useTranslation("records");

  const { data: systemInfo } = useQuery({
    queryKey: ["system", "info"],
    queryFn: () => apiClient.get<SystemInfo>("/system/info").then((r) => r.data),
  });
  const availableBases = systemInfo?.available_bases ?? [];

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { base: "", from_date: "" },
  });

  useEffect(() => {
    if (availableBases.length > 0 && !form.getValues("base")) {
      form.setValue("base", availableBases[0]);
    }
  }, [availableBases, form]);

  const { data: locks = [] } = useQuery<string[]>({
    queryKey: ["system", "locks"],
    queryFn: () => apiClient.get<string[]>("/system/locks").then((r) => r.data),
  });

  const selectedBase = form.watch("base");
  const isBaseLocked = locks.includes(`catalog_sync_${selectedBase}`);

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      apiClient.post("/catalog-records/sync", {
        base: values.base,
        from_date: values.from_date || null,
      }),
    onSuccess: () => form.reset(),
    onError: (error: AxiosError) => {
      if (error.response?.status === 409) {
        queryClient.invalidateQueries({ queryKey: ["system", "locks"] });
        toast.warning(t("addition.sync.locked"));
      } else {
        toast.error(t("common:error"));
      }
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("addition.sync.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
            className="flex items-end gap-4"
          >
            <FormField
              control={form.control}
              name="base"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("addition.sync.base")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {availableBases.map((base) => (
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
              name="from_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("addition.sync.from-date")}</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} className="w-48" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={mutation.isPending || isBaseLocked}>
              {isBaseLocked ? t("addition.sync.locked") : t("addition.sync.submit")}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

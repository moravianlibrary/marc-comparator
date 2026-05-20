import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
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

const schema = z.object({
  base: z.string().min(1),
  from_date: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export function SyncForm() {
  const { t } = useTranslation("records");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { base: "MZK01", from_date: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      apiClient.post("/catalog-records/sync", {
        base: values.base,
        from_date: values.from_date || null,
      }),
    onSuccess: () => {
      toast.success(t("addition.sync.title"));
      form.reset();
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
                  <FormControl>
                    <Input {...field} className="w-32" />
                  </FormControl>
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
            <Button type="submit" disabled={mutation.isPending}>
              {t("addition.sync.submit")}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

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
  system_number: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

export function FetchSingleForm() {
  const { t } = useTranslation("records");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { base: "MZK01", system_number: "" },
  });

  const mutation = useMutation({
    mutationFn: (data: FormValues) =>
      apiClient.post("/catalog-records/fetch", data),
    onSuccess: () => {
      toast.success(t("addition.fetch-single.title"));
      form.reset();
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {t("addition.fetch-single.title")}
        </CardTitle>
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
                  <FormLabel>{t("addition.fetch-single.base")}</FormLabel>
                  <FormControl>
                    <Input {...field} className="w-32" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="system_number"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {t("addition.fetch-single.system-number")}
                  </FormLabel>
                  <FormControl>
                    <Input {...field} className="w-48" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={mutation.isPending}>
              {t("addition.fetch-single.submit")}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

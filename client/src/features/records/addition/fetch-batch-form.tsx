import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

const schema = z.object({
  base: z.string().min(1),
  system_numbers_text: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

export function FetchBatchForm() {
  const { t } = useTranslation("records");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { base: "MZK01", system_numbers_text: "" },
  });

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
    onSuccess: () => {
      toast.success(t("addition.fetch-batch.title"));
      form.reset();
    },
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
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
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

import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SystemInfo } from "@/types/settings";

export function SystemPage() {
  const { t } = useTranslation("system");

  const { data: info, isLoading } = useQuery<SystemInfo>({
    queryKey: ["system", "info"],
    queryFn: () => apiClient.get<SystemInfo>("/system/info").then((r) => r.data),
  });

  const rebuildAnalyticalDataMutation = useMutation({
    mutationFn: () => apiClient.post("/system/rebuild-analytical-data"),
    onSuccess: () => {
      toast.success(t("rebuild-analytical-data.title"));
    },
  });

  function formatUptime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="text-muted-foreground">{t("description")}</p>

      {isLoading ? (
        <p className="text-muted-foreground">{t("common:loading")}</p>
      ) : info ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("info.title")}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
              <dt className="text-muted-foreground">{t("info.version")}</dt>
              <dd>{info.system_version}</dd>

              <dt className="text-muted-foreground">{t("info.commit")}</dt>
              <dd className="font-mono text-xs">{info.system_commit}</dd>

              <dt className="text-muted-foreground">{t("info.uptime")}</dt>
              <dd>{formatUptime(info.uptime_seconds)}</dd>

              <dt className="text-muted-foreground">{t("info.bases")}</dt>
              <dd className="flex gap-1 flex-wrap">
                {info.available_bases.map((base) => (
                  <Badge key={base} variant="outline">{base}</Badge>
                ))}
              </dd>

              <dt className="text-muted-foreground">{t("info.comparators")}</dt>
              <dd>{info.enabled_comparators.join(", ") || "-"}</dd>

              <dt className="text-muted-foreground">{t("info.validators")}</dt>
              <dd>{info.enabled_validators.join(", ") || "-"}</dd>
            </dl>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("rebuild-analytical-data.title")}</CardTitle>
          <CardDescription>{t("rebuild-analytical-data.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={() => rebuildAnalyticalDataMutation.mutate()}
            disabled={rebuildAnalyticalDataMutation.isPending}
          >
            {t("rebuild-analytical-data.action")}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

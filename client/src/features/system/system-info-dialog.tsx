import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { SystemInfo } from "@/types/settings";

interface Props {
  open: boolean;
  onClose: () => void;
}

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

export function SystemInfoDialog({ open, onClose }: Props) {
  const { t } = useTranslation("system");

  const { data: info, isLoading } = useQuery<SystemInfo>({
    queryKey: ["system", "info"],
    queryFn: () => apiClient.get<SystemInfo>("/system/info").then((r) => r.data),
    enabled: open,
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("info.title")}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <p className="text-muted-foreground">{t("common:loading")}</p>
        ) : info ? (
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

            <dt className="text-muted-foreground">{t("info.validators")}</dt>
            <dd>{info.enabled_validators.join(", ") || "-"}</dd>
          </dl>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

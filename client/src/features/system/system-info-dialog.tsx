import { useTranslation } from "react-i18next";
import { Fragment } from "react";
import { useSystemInfo } from "@/hooks/use-system-info";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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

  const { data: info, isLoading } = useSystemInfo(open);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("info.title")}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Fragment key={i}>
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-full" />
              </Fragment>
            ))}
          </div>
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

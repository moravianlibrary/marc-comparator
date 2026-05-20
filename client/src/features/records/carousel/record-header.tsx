import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import type { RecordSummary } from "../types";

interface RecordHeaderProps {
  record: RecordSummary;
}

export function RecordHeader({ record }: RecordHeaderProps) {
  const { t } = useTranslation("records");

  return (
    <div className="space-y-2 border-b pb-4">
      <h2 className="text-lg font-semibold">
        {record.base}-{record.system_number}
      </h2>

      {record.title && <p className="text-base">{record.title}</p>}

      <div className="flex flex-wrap gap-1">
        {record.state.map((s) => (
          <Badge key={s} variant="outline">
            {t(`state.${s}`)}
          </Badge>
        ))}
      </div>

      <div className="flex gap-4 text-xs text-muted-foreground">
        {record.authority_links_count > 0 && (
          <span>
            {t("table.columns.authority-links")}: {record.authority_links_count}
          </span>
        )}
        {record.comparisons_count > 0 && (
          <span>
            {t("table.columns.comparisons")}: {record.comparisons_count}
          </span>
        )}
        {record.validations_count > 0 && (
          <span>
            {t("table.columns.validations")}: {record.validations_count}
          </span>
        )}
      </div>

      <div className="flex gap-4 text-xs text-muted-foreground">
        {record.latest_sync && (
          <span>
            {t("table.columns.latest-sync")}:{" "}
            {new Date(record.latest_sync).toLocaleString("cs-CZ")}
          </span>
        )}
      </div>
    </div>
  );
}

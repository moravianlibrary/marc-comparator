import { useTranslation } from "react-i18next";
import { Link2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { STATE_COLORS, type RecordSummary } from "../types";
import { RecordTaskActions, AdvancedTaskActions } from "../record-task-actions";

interface RecordHeaderProps {
  record: RecordSummary;
  onSelectView?: (viewKey: string) => void;
}

export function RecordHeader({ record, onSelectView }: RecordHeaderProps) {
  const { t } = useTranslation("records");
  const filters = { record_ids: [record.id] };

  return (
    <div className="space-y-2 border-b pb-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {record.base}-{record.system_number}
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => {
              const url = new URL(window.location.origin + window.location.pathname);
              url.searchParams.set("tab", "carousel");
              url.searchParams.set("recordId", record.id);
              navigator.clipboard.writeText(url.toString());
              toast.success(t("carousel.link-copied"));
            }}
            title={t("carousel.permalink")}
          >
            <Link2 className="h-4 w-4" />
          </Button>
          <RecordTaskActions filters={filters} totalCount={1} />
          <AdvancedTaskActions filters={filters} totalCount={1} />
        </div>
      </div>

      {record.title && <p className="text-base">{record.title}</p>}

      {record.authors.length > 0 && (
        <p className="text-sm text-muted-foreground">{record.authors.join(", ")}</p>
      )}

      <div className="flex flex-wrap gap-1">
        {record.type_of_record && (
          <Badge variant="outline" className="text-xs">
            {t(`type-of-record.${record.type_of_record}`, { defaultValue: record.type_of_record })}
          </Badge>
        )}
        {record.bibliographic_level && (
          <Badge variant="outline" className="text-xs">
            {t(`bibliographic-level.${record.bibliographic_level}`, { defaultValue: record.bibliographic_level })}
          </Badge>
        )}
        {record.state.map((s) => (
          <Badge key={s} variant="outline" className={cn("text-xs", STATE_COLORS[s])}>
            {t(`state.${s}`)}
          </Badge>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        {record.authority_links.map((al) => {
          const systemNumber = al.authority_record_id.startsWith(al.base + "-")
            ? al.authority_record_id.slice(al.base.length + 1)
            : al.authority_record_id;
          const viewKey = `auth:${al.base}:${systemNumber}`;
          return (
            <Badge
              key={`${al.linker}-${al.base}`}
              variant="outline"
              className={cn("text-xs", onSelectView && "cursor-pointer hover:bg-accent")}
              onClick={onSelectView ? () => onSelectView(viewKey) : undefined}
            >
              {t("carousel.authority-linked", { base: al.base })}
            </Badge>
          );
        })}
        {record.comparisons.map((c) => {
          const viewKey = `comp:${c.comparator}:${c.other_record_id}`;
          return (
            <Badge
              key={`${c.comparator}-${c.other_record_id}`}
              variant="outline"
              className={cn(
                "text-xs",
                c.match_quality === "Excellent" && "border-green-500 text-green-700 dark:text-green-400",
                c.match_quality === "Moderate" && "border-yellow-500 text-yellow-700 dark:text-yellow-400",
                c.match_quality === "Poor" && "border-red-500 text-red-700 dark:text-red-400",
                onSelectView && "cursor-pointer hover:bg-accent",
              )}
              onClick={onSelectView ? () => onSelectView(viewKey) : undefined}
            >
              {c.base}: {(c.overall_score * 100).toFixed(0)}%
            </Badge>
          );
        })}
        {record.validations.map((v, i) => {
          const viewKey = `val:${v.validator}`;
          return (
            <Badge
              key={i}
              variant="outline"
              className={cn(
                "text-xs",
                v.status === "Valid" && "border-green-500 text-green-700 dark:text-green-400",
                v.status === "Invalid" && "border-red-500 text-red-700 dark:text-red-400",
                v.status === "ForReview" && "border-yellow-500 text-yellow-700 dark:text-yellow-400",
                onSelectView && "cursor-pointer hover:bg-accent",
              )}
              onClick={onSelectView ? () => onSelectView(viewKey) : undefined}
            >
              {t(`validator-name.${v.validator}`)} [{v.target_tag}]: {t(`validity-status.${v.status}`)}
            </Badge>
          );
        })}
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

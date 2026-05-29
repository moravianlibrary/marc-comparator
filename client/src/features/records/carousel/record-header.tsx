import { useTranslation } from "react-i18next";
import { Link2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import { STATE_COLORS, type RecordSummary, type ValidationSummary } from "../types";
import { RecordTaskActions, AdvancedTaskActions } from "../record-task-actions";
import { groupValidations, VALIDATION_BADGE_CLASS, COMPARISON_BADGE_CLASS } from "../utils";

interface RecordHeaderProps {
  record: RecordSummary;
  onSelectView?: (viewKey: string) => void;
}

export function RecordHeader({ record, onSelectView }: RecordHeaderProps) {
  const { t } = useTranslation("records");
  const { hasPermission } = useHasPermission();
  const canProcess = hasPermission(Permission.ProcessRecords) === true;
  const canRunPartial = hasPermission(Permission.RunPartialRecordTasks) === true;
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
          {canProcess && <RecordTaskActions filters={filters} totalCount={1} />}
          {canRunPartial && <AdvancedTaskActions filters={filters} totalCount={1} />}
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
                COMPARISON_BADGE_CLASS[c.match_quality],
                onSelectView && "cursor-pointer hover:bg-accent",
              )}
              onClick={onSelectView ? () => onSelectView(viewKey) : undefined}
            >
              {c.base}: {(c.overall_score * 100).toFixed(0)}%
            </Badge>
          );
        })}
        {groupValidations(record.validations).map((g) => {
          const viewKey = `val:${g.validator}`;
          return (
            <Badge
              key={`${g.validator}-${g.target_tag}-${g.status}`}
              variant="outline"
              className={cn(
                "text-xs",
                VALIDATION_BADGE_CLASS[g.status],
                onSelectView && "cursor-pointer hover:bg-accent",
              )}
              onClick={onSelectView ? () => onSelectView(viewKey) : undefined}
            >
              {t(`validator-name.${g.validator}`)} [{g.target_tag}]: {t(`validity-status.${g.status}`)}
              {g.count > 1 && (
                <span className="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-muted-foreground/20 px-1 text-[10px] font-medium">
                  {g.count}
                </span>
              )}
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

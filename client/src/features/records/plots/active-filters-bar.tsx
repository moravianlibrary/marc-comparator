import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface ActiveFilter {
  facetField: string;
  label: string;
  value: string;
  valueLabel: string;
}

interface ActiveFiltersBarProps {
  activeFilters: ActiveFilter[];
  hasScoreFilter: boolean;
  hasRecordIdFilter: boolean;
  recordId: string;
  scoreMin: number;
  scoreMax: number;
  onToggleFilter: (facetField: string, value: string) => void;
  onClearRecordId: () => void;
  onClearScore: () => void;
  onClearAll: () => void;
}

export function ActiveFiltersBar({
  activeFilters,
  hasScoreFilter,
  hasRecordIdFilter,
  recordId,
  scoreMin,
  scoreMax,
  onToggleFilter,
  onClearRecordId,
  onClearScore,
  onClearAll,
}: ActiveFiltersBarProps) {
  const { t } = useTranslation("records");

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm font-medium text-muted-foreground">
        {t("plots.active-filters")}:
      </span>
      {activeFilters.map((af) => (
        <Badge
          key={`${af.facetField}-${af.value}`}
          variant="secondary"
          className="gap-1 cursor-pointer"
          onClick={() => onToggleFilter(af.facetField, af.value)}
        >
          <span className="text-muted-foreground">{af.label}:</span> {af.valueLabel}
          <X className="h-3 w-3" />
        </Badge>
      ))}
      {hasRecordIdFilter && (
        <Badge variant="secondary" className="gap-1 cursor-pointer" onClick={onClearRecordId}>
          <span className="text-muted-foreground">{t("plots.record-id")}:</span> {recordId}
          <X className="h-3 w-3" />
        </Badge>
      )}
      {hasScoreFilter && (
        <Badge variant="secondary" className="gap-1 cursor-pointer" onClick={onClearScore}>
          <span className="text-muted-foreground">{t("facet-fields.overall_score")}:</span>{" "}
          {(scoreMin * 100).toFixed(0)}–{(scoreMax * 100).toFixed(0)}%
          <X className="h-3 w-3" />
        </Badge>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="h-6 text-xs text-muted-foreground"
        onClick={onClearAll}
      >
        {t("plots.clear-all")}
      </Button>
    </div>
  );
}

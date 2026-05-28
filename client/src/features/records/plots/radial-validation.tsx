import { useMemo } from "react";
import { cn } from "@/lib/utils";
import { RadialBarChart, RadialBar, PolarAngleAxis, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import { FacetTooltip } from "./facet-tooltip";
import { useTranslation } from "react-i18next";
import type { FacetBucket } from "../types";

interface RadialValidationProps {
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

const STATUS_ORDER = ["AdditionalInfo", "Invalid", "ForReview", "Valid"] as const;

export const STATUS_COLORS: Record<string, string> = {
  Valid: "var(--status-success)",
  ForReview: "var(--status-warning)",
  Invalid: "var(--status-danger)",
  AdditionalInfo: "var(--status-info)",
};

export function RadialValidation({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: RadialValidationProps) {
  const { t } = useTranslation("records");
  const chartConfig = useMemo<ChartConfig>(() => ({
    count: { label: t("common:chart.count") },
    preview: { label: t("common:chart.preview") },
    Valid: { label: t("validity-status.Valid"), color: "var(--status-success)" },
    ForReview: { label: t("validity-status.ForReview"), color: "var(--status-warning)" },
    Invalid: { label: t("validity-status.Invalid"), color: "var(--status-danger)" },
    AdditionalInfo: { label: t("validity-status.AdditionalInfo"), color: "var(--status-info)" },
  }), [t]);

  const isShowingPreview = previewData != null;

  const total = data.reduce((sum, b) => sum + b.count, 0);
  const previewTotal = isShowingPreview
    ? previewData.reduce((sum, b) => sum + b.count, 0)
    : 0;

  // One entry per status, rendered as concentric rings (innermost first in data)
  const chartData = STATUS_ORDER.map((status) => {
    const bucket = data.find((b) => b.key === status);
    const previewCount = previewData?.find((p) => p.key === status)?.count ?? 0;
    // Scale preview relative to previewTotal so shadow tracks fill proportionally
    const minArc = total * 0.03;
    const rawPreview =
      isShowingPreview && previewTotal > 0
        ? Math.min((previewCount / previewTotal) * total, total * 0.999)
        : previewCount;
    const scaledPreview = rawPreview > 0 ? Math.max(rawPreview, minArc) : 0;
    return {
      name: t(`validity-status.${status}`),
      key: status,
      count: bucket?.count ?? 0,
      preview: scaledPreview,
      rawPreview: previewCount,
      fill: `var(--color-${status})`,
    };
  });

  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-shrink-0" style={{ width: 300, height: 300 }}>
        <ChartContainer config={chartConfig} className="aspect-square [&_.recharts-wrapper]:z-10" style={{ width: 300, height: 300 }}>
          <RadialBarChart
            data={chartData}
            startAngle={-90}
            endAngle={270}
            innerRadius="40%"
            outerRadius="90%"
            barSize={14}
          >
            <PolarAngleAxis type="number" domain={[0, total || 1]} tick={false} />
            <ChartTooltip
              cursor={false}
              content={<FacetTooltip previewKey="rawPreview" />}
            />
            <RadialBar
              dataKey="count"
              cornerRadius={4}
              cursor="pointer"
              background={isShowingPreview ? undefined : { fill: "var(--muted)" }}
              onClick={(entry) => {
                if (entry.count === 0) return;
                if (isShowingPreview && entry.rawPreview === 0) return;
                onToggle(entry.key);
              }}
              onMouseEnter={(_, index) => onHover(chartData[index].key)}
              onMouseLeave={onLeave}
            />
            {isShowingPreview && (
              <RadialBar
                dataKey="preview"
                cornerRadius={4}
                isAnimationActive={false}
              >
                {chartData.map((entry) => (
                  <Cell
                    key={entry.key}
                    fill={`color-mix(in oklch, ${STATUS_COLORS[entry.key]} 25%, transparent)`}
                  />
                ))}
              </RadialBar>
            )}
          </RadialBarChart>
        </ChartContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="flex flex-col items-center">
            <p className={cn("font-bold tabular-nums", total > 999999 ? "text-xs" : total > 99999 ? "text-sm" : total > 9999 ? "text-lg" : "text-2xl")}>
              {total.toLocaleString("cs-CZ")}
            </p>
            {isShowingPreview && (
              <p className="text-xs tabular-nums text-muted-foreground">
                {previewTotal.toLocaleString("cs-CZ")}
              </p>
            )}
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-2 text-xs">
        {STATUS_ORDER.toReversed().map((status) => {
          const bucket = data.find((b) => b.key === status);
          const count = bucket?.count ?? 0;
          const previewCount = previewData?.find((p) => p.key === status)?.count ?? 0;
          const isActive = activeValues.includes(status);
          const isDisabled = !isActive && (count === 0 || (isShowingPreview && previewCount === 0));
          return (
            <button
              key={status}
              disabled={isDisabled}
              className={cn(
                "flex items-center gap-2 transition-opacity text-left",
                isDisabled
                  ? "opacity-30 cursor-not-allowed"
                  : activeValues.length > 0 && !isActive && "opacity-40",
              )}
              onClick={() => onToggle(status)}
              onMouseEnter={() => onHover(status)}
              onMouseLeave={onLeave}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: STATUS_COLORS[status] }}
              />
              <span className="whitespace-nowrap">{t(`validity-status.${status}`)}</span>
              <span className="tabular-nums text-foreground">
                {count.toLocaleString("cs-CZ")}
              </span>
              {isShowingPreview && (
                <span className="tabular-nums text-muted-foreground">
                  {previewCount.toLocaleString("cs-CZ")}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

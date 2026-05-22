import { useMemo } from "react";
import { cn } from "@/lib/utils";
import { RadialBarChart, RadialBar, PolarAngleAxis, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { useTranslation } from "react-i18next";
import type { FacetBucket } from "../types";

interface RadialQualityProps {
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

const QUALITY_ORDER = ["Poor", "Moderate", "Excellent"] as const;

const QUALITY_COLORS: Record<string, string> = {
  Excellent: "var(--status-success)",
  Moderate: "var(--status-warning)",
  Poor: "var(--status-danger)",
};

export function RadialQuality({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: RadialQualityProps) {
  const { t } = useTranslation("records");
  const chartConfig = useMemo<ChartConfig>(() => ({
    count: { label: t("common:chart.count") },
    preview: { label: t("common:chart.preview") },
    Excellent: { label: t("match-quality.Excellent"), color: "var(--status-success)" },
    Moderate: { label: t("match-quality.Moderate"), color: "var(--status-warning)" },
    Poor: { label: t("match-quality.Poor"), color: "var(--status-danger)" },
  }), [t]);

  const isShowingPreview = previewData != null;

  const total = data.reduce((sum, b) => sum + b.count, 0);
  const previewTotal = isShowingPreview
    ? previewData.reduce((sum, b) => sum + b.count, 0)
    : 0;

  // Build one data entry per quality level for stacked display
  const chartData = QUALITY_ORDER.map((quality) => {
    const bucket = data.find((b) => b.key === quality);
    const previewCount = previewData?.find((p) => p.key === quality)?.count ?? 0;
    // Scale preview relative to previewTotal so shadow tracks fill proportionally
    const scaledPreview =
      isShowingPreview && previewTotal > 0
        ? Math.min((previewCount / previewTotal) * total, total * 0.999)
        : previewCount;
    return {
      name: t(`match-quality.${quality}`),
      key: quality,
      count: bucket?.count ?? 0,
      preview: scaledPreview,
      rawPreview: previewCount,
      fill: `var(--color-${quality})`,
    };
  });


  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full overflow-hidden" style={{ height: 160 }}>
        <ChartContainer config={chartConfig} className="w-full" style={{ height: 320 }}>
          <RadialBarChart
            data={chartData}
            startAngle={180}
            endAngle={0}
            innerRadius="40%"
            outerRadius="100%"
            barSize={16}
          >
            <PolarAngleAxis type="number" domain={[0, total || 1]} tick={false} />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent nameKey="name" />}
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
                    fill={`color-mix(in oklch, ${QUALITY_COLORS[entry.key]} 25%, transparent)`}
                  />
                ))}
              </RadialBar>
            )}
            <RadialBar
              dataKey="count"
              cornerRadius={4}
              cursor="pointer"
              onClick={(entry) => {
                if (entry.count === 0) return;
                if (isShowingPreview && entry.rawPreview === 0) return;
                onToggle(entry.key);
              }}
              onMouseEnter={(_, index) => onHover(chartData[index].key)}
              onMouseLeave={onLeave}
            />
          </RadialBarChart>
        </ChartContainer>
        <div className="absolute bottom-0 left-0 right-0 flex flex-col items-center pointer-events-none">
          <p className="text-2xl font-bold tabular-nums">
            {total.toLocaleString("cs-CZ")}
          </p>
          {isShowingPreview && (
            <p className="text-xs tabular-nums text-muted-foreground">
              {previewTotal.toLocaleString("cs-CZ")}
            </p>
          )}
        </div>
      </div>
      <div className="flex gap-4 mt-2 text-xs">
        {QUALITY_ORDER.toReversed().map((quality) => {
          const bucket = data.find((b) => b.key === quality);
          const count = bucket?.count ?? 0;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          const previewCount = previewData?.find((p) => p.key === quality)?.count ?? 0;
          const previewPct = isShowingPreview && previewTotal > 0
            ? Math.round((previewCount / previewTotal) * 100)
            : 0;
          const isActive = activeValues.includes(quality);
          const isDisabled = !isActive && (count === 0 || (isShowingPreview && previewCount === 0));
          return (
            <button
              key={quality}
              disabled={isDisabled}
              className={cn(
                "flex items-center gap-1 transition-opacity",
                isDisabled
                  ? "opacity-30 cursor-not-allowed"
                  : activeValues.length > 0 && !isActive && "opacity-40",
              )}
              onClick={() => onToggle(quality)}
              onMouseEnter={() => onHover(quality)}
              onMouseLeave={onLeave}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: QUALITY_COLORS[quality] }}
              />
              <span>{t(`match-quality.${quality}`)}</span>
              <span className="tabular-nums text-foreground">{pct}%</span>
              {isShowingPreview && (
                <span className="tabular-nums text-muted-foreground">{previewPct}%</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

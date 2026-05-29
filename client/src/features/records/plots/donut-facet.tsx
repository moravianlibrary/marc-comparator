import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { PieChart, Pie, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import { FacetTooltip } from "./facet-tooltip";
import { cn } from "@/lib/utils";
import type { FacetBucket } from "../types";

const COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

interface DonutFacetProps {
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
  formatLabel?: (key: string) => string;
}

export function DonutFacet({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
  formatLabel,
}: DonutFacetProps) {
  const { t } = useTranslation();
  const chartConfig = useMemo<ChartConfig>(() => ({
    count: { label: t("common:chart.count") },
  }), [t]);

  const isShowingPreview = previewData != null;

  const fmt = formatLabel ?? ((k: string) => k);

  const chartData = data.map((bucket, index) => {
    const previewCount = previewData?.find((p) => p.key === bucket.key)?.count ?? 0;
    return {
      key: bucket.key,
      name: fmt(bucket.key),
      count: bucket.count,
      preview: previewCount,
      fill: COLORS[index % COLORS.length],
    };
  });

  const total = chartData.reduce((sum, d) => sum + d.count, 0);
  const previewTotal = isShowingPreview
    ? previewData.reduce((sum, b) => sum + b.count, 0)
    : 0;

  // Scale preview values relative to previewTotal so shadow tracks fill proportionally
  const previewChartData = isShowingPreview
    ? data.map((bucket, index) => {
        const previewCount = previewData.find((p) => p.key === bucket.key)?.count ?? 0;
        const scaledValue =
          previewTotal > 0
            ? (previewCount / previewTotal) * total
            : previewCount;
        return {
          key: bucket.key,
          name: fmt(bucket.key),
          count: scaledValue,
          fill: COLORS[index % COLORS.length],
        };
      })
    : [];

  const dominant =
    chartData.length > 0
      ? chartData.reduce((a, b) => (a.count >= b.count ? a : b))
      : null;
  const dominantPercent =
    dominant && total > 0
      ? Math.round((dominant.count / total) * 100)
      : 0;

  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-shrink-0">
        <ChartContainer config={chartConfig} className="aspect-square" style={{ width: 240, height: 240 }}>
          <PieChart>
            {/* Preview data as faded background */}
            {isShowingPreview && (
              <Pie
                data={previewChartData}
                dataKey="count"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={68}
                outerRadius={105}
                isAnimationActive={false}
              >
                {previewChartData.map((entry) => (
                  <Cell
                    key={`bg-${entry.name}`}
                    fill="color-mix(in oklch, var(--muted-foreground) 15%, transparent)"
                  />
                ))}
              </Pie>
            )}
            {/* Original data always on top */}
            <Pie
              data={chartData}
              dataKey="count"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={68}
              outerRadius={105}
              cursor="pointer"
              onClick={(entry) => {
                if (isShowingPreview && entry.preview === 0) return;
                onToggle(entry.key);
              }}
              onMouseEnter={(_, index) => onHover(chartData[index].key)}
              onMouseLeave={onLeave}
            >
              {chartData.map((entry) => {
                const isDisabledSegment = isShowingPreview && !activeValues.includes(entry.key) && entry.preview === 0;
                return (
                  <Cell
                    key={entry.key}
                    fill={entry.fill}
                    opacity={
                      isDisabledSegment
                        ? 0.15
                        : activeValues.length === 0 || activeValues.includes(entry.key)
                          ? 1
                          : 0.3
                    }
                    cursor={isDisabledSegment ? "default" : "pointer"}
                  />
                );
              })}
            </Pie>
            <ChartTooltip
              cursor={false}
              content={<FacetTooltip />}
            />
            {dominant && (
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="central"
                className="fill-foreground"
              >
                <tspan x="50%" dy="-0.4em" fontSize={18} fontWeight={600}>
                  {dominantPercent}%
                </tspan>
                <tspan x="50%" dy="1.4em" fontSize={11} className="fill-muted-foreground">
                  {dominant.name}
                </tspan>
              </text>
            )}
          </PieChart>
        </ChartContainer>
      </div>
      <div className="flex flex-col gap-2 text-xs">
        {chartData.map((entry, index) => {
          const isActive = activeValues.includes(entry.key);
          const isDisabled = isShowingPreview && !isActive && entry.preview === 0;
          return (
            <button
              key={entry.key}
              disabled={isDisabled}
              className={cn(
                "flex items-center gap-2 transition-opacity text-left",
                isDisabled
                  ? "opacity-30 cursor-not-allowed"
                  : activeValues.length > 0 && !isActive && "opacity-40",
              )}
              onClick={() => onToggle(entry.key)}
              onMouseEnter={() => onHover(entry.key)}
              onMouseLeave={onLeave}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span className="whitespace-nowrap">{entry.name}</span>
              <span className="tabular-nums text-foreground">
                {entry.count.toLocaleString("cs-CZ")}
              </span>
              <span
                className="tabular-nums text-muted-foreground fade-toggle"
                data-visible={isShowingPreview}
              >
                {entry.preview.toLocaleString("cs-CZ")}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

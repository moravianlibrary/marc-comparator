import { useMemo, useRef } from "react";
import { cn } from "@/lib/utils";
import { PieChart, Pie, Cell } from "recharts";
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart";
import { FacetTooltip } from "./facet-tooltip";
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
  const chartConfig = useMemo<ChartConfig>(
    () => ({
      count: { label: t("common:chart.count") },
      preview: { label: t("common:chart.preview") },
      Excellent: { label: t("match-quality.Excellent"), color: "var(--status-success)" },
      Moderate: { label: t("match-quality.Moderate"), color: "var(--status-warning)" },
      Poor: { label: t("match-quality.Poor"), color: "var(--status-danger)" },
    }),
    [t],
  );

  const isShowingPreview = previewData != null;
  const wasShowingPreview = useRef(false);
  const justStartedPreview = isShowingPreview && !wasShowingPreview.current;
  wasShowingPreview.current = isShowingPreview;

  const total = data.reduce((sum, b) => sum + b.count, 0);
  const previewTotal = isShowingPreview ? previewData.reduce((sum, b) => sum + b.count, 0) : 0;

  const mainSegments = QUALITY_ORDER.map((quality) => {
    const bucket = data.find((b) => b.key === quality);
    const previewCount = previewData?.find((p) => p.key === quality)?.count ?? 0;
    return {
      name: t(`match-quality.${quality}`),
      key: quality,
      count: bucket?.count ?? 0,
      preview: previewCount,
      fill: QUALITY_COLORS[quality],
    };
  });

  const previewSegments = QUALITY_ORDER.map((quality) => {
    const count = previewData?.find((p) => p.key === quality)?.count ?? 0;
    return {
      name: t(`match-quality.${quality}`),
      key: quality,
      count,
    };
  });

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full" style={{ height: 160 }}>
        <ChartContainer
          config={chartConfig}
          className="w-full [&_.recharts-wrapper]:z-10 [&_.recharts-pie]:transition-opacity [&_.recharts-pie]:duration-300"
          style={{ height: 320 }}
        >
          <PieChart>
            <ChartTooltip cursor={false} content={<FacetTooltip />} />
            <Pie
              data={
                isShowingPreview
                  ? previewSegments
                  : previewSegments.map((s) => ({ ...s, count: 0 }))
              }
              dataKey="count"
              nameKey="name"
              startAngle={180}
              endAngle={0}
              innerRadius="55%"
              outerRadius="68%"
              paddingAngle={1}
              cornerRadius={4}
              isAnimationActive={justStartedPreview}
              animationDuration={300}
            >
              {previewSegments.map((entry) => (
                <Cell
                  key={entry.key}
                  fill={`color-mix(in oklch, ${QUALITY_COLORS[entry.key]} 25%, transparent)`}
                />
              ))}
            </Pie>
            <Pie
              data={mainSegments}
              dataKey="count"
              nameKey="name"
              startAngle={180}
              endAngle={0}
              innerRadius={isShowingPreview ? "74%" : "70%"}
              outerRadius={isShowingPreview ? "88%" : "84%"}
              paddingAngle={1}
              cornerRadius={4}
              cursor="pointer"
              onClick={(_, index) => {
                const entry = mainSegments[index];
                if (entry.count === 0) return;
                if (isShowingPreview && entry.preview === 0) return;
                onToggle(entry.key);
              }}
              onMouseEnter={(_, index) => onHover(mainSegments[index].key)}
              onMouseLeave={onLeave}
            >
              {mainSegments.map((entry) => (
                <Cell key={entry.key} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <div className="absolute bottom-0 left-0 right-0 flex flex-col items-center pointer-events-none">
          <p
            className={cn(
              "font-bold tabular-nums",
              total > 999999
                ? "text-xs"
                : total > 99999
                  ? "text-sm"
                  : total > 9999
                    ? "text-lg"
                    : "text-2xl",
            )}
          >
            {total.toLocaleString("cs-CZ")}
          </p>
          <span
            className="text-xs tabular-nums text-muted-foreground fade-toggle"
            data-visible={isShowingPreview}
          >
            {previewTotal.toLocaleString("cs-CZ")}
          </span>
        </div>
      </div>
      <div className="flex gap-4 mt-2 text-xs">
        {QUALITY_ORDER.toReversed().map((quality) => {
          const segment = mainSegments.find((s) => s.key === quality)!;
          const pct = total > 0 ? Math.round((segment.count / total) * 100) : 0;
          const previewPct =
            isShowingPreview && previewTotal > 0
              ? Math.round((segment.preview / previewTotal) * 100)
              : 0;
          const isActive = activeValues.includes(quality);
          const isDisabled =
            !isActive && (segment.count === 0 || (isShowingPreview && segment.preview === 0));
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
              <span
                className="tabular-nums text-muted-foreground fade-toggle"
                data-visible={isShowingPreview}
              >
                {previewPct}%
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

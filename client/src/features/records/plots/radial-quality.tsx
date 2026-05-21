import { cn } from "@/lib/utils";
import { RadialBarChart, RadialBar, PolarAngleAxis } from "recharts";
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

const chartConfig = {
  count: { label: "Count" },
  Excellent: { label: "Excellent", color: "var(--status-success)" },
  Moderate: { label: "Moderate", color: "var(--status-warning)" },
  Poor: { label: "Poor", color: "var(--status-danger)" },
} satisfies ChartConfig;

export function RadialQuality({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: RadialQualityProps) {
  const { t } = useTranslation("records");
  const isShowingPreview = previewData && previewData.length > 0;

  const total = data.reduce((sum, b) => sum + b.count, 0);

  // Build one data entry per quality level for stacked display
  const chartData = QUALITY_ORDER.map((quality) => {
    const bucket = data.find((b) => b.key === quality);
    const preview = previewData?.find((p) => p.key === quality);
    const count = isShowingPreview ? (preview?.count ?? 0) : (bucket?.count ?? 0);
    return {
      name: t(`match-quality.${quality}`),
      key: quality,
      count,
      fill: `var(--color-${quality})`,
    };
  });

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full" style={{ height: 160 }}>
        <div className="absolute inset-0" style={{ top: 0, height: 320, overflow: "hidden" }}>
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
              <RadialBar
                dataKey="count"
                cornerRadius={4}
                cursor="pointer"
                onClick={(entry) => onToggle(entry.key)}
                onMouseEnter={(_, index) => onHover(chartData[index].key)}
                onMouseLeave={onLeave}
              />
            </RadialBarChart>
          </ChartContainer>
        </div>
        <div className="absolute bottom-0 left-0 right-0 flex justify-center pointer-events-none">
          <p className="text-2xl font-bold tabular-nums">
            {total.toLocaleString("cs-CZ")}
          </p>
        </div>
      </div>
      <div className="flex gap-4 mt-2 text-xs">
        {QUALITY_ORDER.toReversed().map((quality) => {
          const bucket = data.find((b) => b.key === quality);
          const count = bucket?.count ?? 0;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <button
              key={quality}
              className={cn(
                "flex items-center gap-1 transition-opacity",
                activeValues.length > 0 && !activeValues.includes(quality) && "opacity-40",
              )}
              onClick={() => onToggle(quality)}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: QUALITY_COLORS[quality] }}
              />
              <span>{t(`match-quality.${quality}`)}</span>
              <span className="text-muted-foreground tabular-nums">{pct}%</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

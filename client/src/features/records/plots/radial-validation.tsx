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

interface RadialValidationProps {
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

const STATUS_ORDER = ["AdditionalInfo", "Invalid", "ForReview", "Valid"] as const;

const STATUS_COLORS: Record<string, string> = {
  Valid: "var(--status-success)",
  ForReview: "var(--status-warning)",
  Invalid: "var(--status-danger)",
  AdditionalInfo: "var(--status-info)",
};

const chartConfig = {
  count: { label: "Count" },
  Valid: { label: "Valid", color: "var(--status-success)" },
  ForReview: { label: "ForReview", color: "var(--status-warning)" },
  Invalid: { label: "Invalid", color: "var(--status-danger)" },
  AdditionalInfo: { label: "AdditionalInfo", color: "var(--status-info)" },
} satisfies ChartConfig;

export function RadialValidation({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: RadialValidationProps) {
  const { t } = useTranslation("records");
  const isShowingPreview = previewData && previewData.length > 0;

  const total = data.reduce((sum, b) => sum + b.count, 0);

  // One entry per status, rendered as concentric rings (innermost first in data)
  const chartData = STATUS_ORDER.map((status) => {
    const bucket = data.find((b) => b.key === status);
    const preview = previewData?.find((p) => p.key === status);
    const count = isShowingPreview ? (preview?.count ?? 0) : (bucket?.count ?? 0);
    return {
      name: t(`validity-status.${status}`),
      key: status,
      count,
      fill: `var(--color-${status})`,
    };
  });

  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-shrink-0">
        <ChartContainer config={chartConfig} className="aspect-square" style={{ width: 180, height: 180 }}>
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
              content={<ChartTooltipContent nameKey="name" />}
            />
            <RadialBar
              dataKey="count"
              cornerRadius={4}
              cursor="pointer"
              background={{ fill: "var(--muted)" }}
              onClick={(entry) => onToggle(entry.key)}
              onMouseEnter={(_, index) => onHover(chartData[index].key)}
              onMouseLeave={onLeave}
            />
          </RadialBarChart>
        </ChartContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-2xl font-bold tabular-nums">
            {total.toLocaleString("cs-CZ")}
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-2 text-xs">
        {STATUS_ORDER.toReversed().map((status) => {
          const bucket = data.find((b) => b.key === status);
          const count = bucket?.count ?? 0;
          return (
            <button
              key={status}
              className={cn(
                "flex items-center gap-2 transition-opacity text-left",
                activeValues.length > 0 && !activeValues.includes(status) && "opacity-40",
              )}
              onClick={() => onToggle(status)}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: STATUS_COLORS[status] }}
              />
              <span className="whitespace-nowrap">{t(`validity-status.${status}`)}</span>
              <span className="text-muted-foreground tabular-nums">
                {count.toLocaleString("cs-CZ")}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

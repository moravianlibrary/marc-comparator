import { PieChart, Pie, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
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
}

const chartConfig = {
  value: { label: "Count" },
} satisfies ChartConfig;

export function DonutFacet({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: DonutFacetProps) {
  const isShowingPreview = previewData && previewData.length > 0;

  const chartData = data.map((bucket, index) => {
    const preview = previewData?.find((p) => p.key === bucket.key);
    return {
      name: bucket.key,
      value: isShowingPreview ? (preview?.count ?? 0) : bucket.count,
      fill: COLORS[index % COLORS.length],
    };
  });

  const total = chartData.reduce((sum, d) => sum + d.value, 0);
  const dominant =
    chartData.length > 0
      ? chartData.reduce((a, b) => (a.value >= b.value ? a : b))
      : null;
  const dominantPercent =
    dominant && total > 0 ? Math.round((dominant.value / total) * 100) : 0;

  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-shrink-0">
        <ChartContainer config={chartConfig} className="aspect-square" style={{ width: 180, height: 180 }}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              cursor="pointer"
              onClick={(entry) => onToggle(entry.name)}
              onMouseEnter={(_, index) => onHover(chartData[index].name)}
              onMouseLeave={onLeave}
            >
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={entry.fill}
                  opacity={
                    activeValues.length === 0 || activeValues.includes(entry.name)
                      ? 1
                      : 0.3
                  }
                />
              ))}
            </Pie>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent nameKey="name" />}
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
        {data.map((bucket, index) => {
          const count = isShowingPreview
            ? (previewData?.find((p) => p.key === bucket.key)?.count ?? 0)
            : bucket.count;
          return (
            <button
              key={bucket.key}
              className={cn(
                "flex items-center gap-2 transition-opacity text-left",
                activeValues.length > 0 &&
                  !activeValues.includes(bucket.key) &&
                  "opacity-40",
              )}
              onClick={() => onToggle(bucket.key)}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span className="whitespace-nowrap">{bucket.key}</span>
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

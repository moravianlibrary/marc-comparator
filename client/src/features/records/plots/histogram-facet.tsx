import { BarChart, Bar, XAxis, YAxis, Brush, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { HistogramBucket } from "../types";

interface HistogramFacetProps {
  data: HistogramBucket[];
  onRangeChange: (from: number, to: number) => void;
}

const chartConfig = {
  count: { label: "Count", color: "var(--chart-1)" },
} satisfies ChartConfig;

function getScoreColor(min: number): string {
  if (min >= 0.9) return "var(--status-success)";
  if (min >= 0.7) return "var(--status-warning)";
  return "var(--status-danger)";
}

export function HistogramFacet({ data, onRangeChange }: HistogramFacetProps) {
  const chartData = data.map((bucket) => ({
    range: `${(bucket.min * 100).toFixed(0)}–${(bucket.max * 100).toFixed(0)}%`,
    min: bucket.min,
    max: bucket.max,
    count: bucket.count,
  }));

  function handleBrushChange(brush: {
    startIndex?: number;
    endIndex?: number;
  }) {
    if (brush.startIndex != null && brush.endIndex != null) {
      const from = chartData[brush.startIndex].min;
      const to = chartData[brush.endIndex].max;
      onRangeChange(from, to);
    }
  }

  return (
    <ChartContainer config={chartConfig} className="w-full" style={{ height: 200 }}>
      <BarChart data={chartData}>
        <XAxis dataKey="range" tick={{ fontSize: 10 }} />
        <YAxis hide />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent />}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {chartData.map((entry) => (
            <Cell key={entry.range} fill={getScoreColor(entry.min)} />
          ))}
        </Bar>
        <Brush
          dataKey="range"
          height={20}
          stroke="var(--border)"
          onChange={handleBrushChange}
        />
      </BarChart>
    </ChartContainer>
  );
}

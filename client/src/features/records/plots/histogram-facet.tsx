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

function normalizeBuckets(raw: HistogramBucket[]): HistogramBucket[] {
  // Build a map from bucket min to count
  const countByMin = new Map<number, number>();
  for (const b of raw) {
    // Merge anything >= 1.0 into the "100%" bucket (min=1.0)
    if (b.min >= 1.0) {
      countByMin.set(1.0, (countByMin.get(1.0) ?? 0) + b.count);
    } else {
      const key = Math.round(b.min * 100) / 100; // avoid float drift
      countByMin.set(key, (countByMin.get(key) ?? 0) + b.count);
    }
  }

  // Generate all 5%-wide buckets from 0.00 to 0.90 (inclusive)
  const buckets: HistogramBucket[] = [];
  for (let i = 0; i < 19; i++) {
    const min = Math.round(i * 5) / 100;
    const max = Math.round((i + 1) * 5) / 100;
    buckets.push({ min, max, count: countByMin.get(min) ?? 0 });
  }
  // 95–<100% bucket
  buckets.push({ min: 0.95, max: 1.0, count: countByMin.get(0.95) ?? 0 });
  // Special 100% bucket
  buckets.push({ min: 1.0, max: 1.0, count: countByMin.get(1.0) ?? 0 });

  return buckets;
}

export function HistogramFacet({ data, onRangeChange }: HistogramFacetProps) {
  const normalized = normalizeBuckets(data);

  const chartData = normalized.map((bucket) => {
    let range: string;
    if (bucket.min === 1.0) {
      range = "100%";
    } else if (bucket.min === 0.95) {
      range = "95–<100%";
    } else {
      range = `${(bucket.min * 100).toFixed(0)}–${(bucket.max * 100).toFixed(0)}%`;
    }
    return {
      range,
      min: bucket.min,
      max: bucket.max,
      count: bucket.count,
    };
  });

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

import { BarChart, Bar, XAxis, YAxis, Rectangle } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import { FacetTooltip } from "./facet-tooltip";
import type { HistogramBucket } from "../types";

interface HistogramFacetProps {
  data: HistogramBucket[];
  previewData?: HistogramBucket[];
}

const chartConfig = {
  preview: { label: "Preview", color: "var(--chart-1)" },
  remainder: { label: "Remainder", color: "var(--chart-1)" },
} satisfies ChartConfig;

function getScoreColor(min: number): string {
  if (min >= 0.9) return "var(--status-success)";
  if (min >= 0.7) return "var(--status-warning)";
  return "var(--status-danger)";
}

function normalizeBuckets(raw: HistogramBucket[]): HistogramBucket[] {
  const countByMin = new Map<number, number>();
  for (const b of raw) {
    if (b.min >= 1.0) {
      countByMin.set(1.0, (countByMin.get(1.0) ?? 0) + b.count);
    } else {
      const key = Math.round(b.min * 100) / 100;
      countByMin.set(key, (countByMin.get(key) ?? 0) + b.count);
    }
  }

  const buckets: HistogramBucket[] = [];
  for (let i = 0; i < 19; i++) {
    const min = Math.round(i * 5) / 100;
    const max = Math.round((i + 1) * 5) / 100;
    buckets.push({ min, max, count: countByMin.get(min) ?? 0 });
  }
  buckets.push({ min: 0.95, max: 1.0, count: countByMin.get(0.95) ?? 0 });
  buckets.push({ min: 1.0, max: 1.0, count: countByMin.get(1.0) ?? 0 });

  return buckets;
}

export function HistogramFacet({ data, previewData }: HistogramFacetProps) {
  const normalized = normalizeBuckets(data);
  const normalizedPreview = previewData ? normalizeBuckets(previewData) : null;
  const isShowingPreview = normalizedPreview != null;

  const chartData = normalized.map((bucket, index) => {
    let range: string;
    if (bucket.min === 1.0) {
      range = "100%";
    } else if (bucket.min === 0.95) {
      range = "95–<100%";
    } else {
      range = `${(bucket.min * 100).toFixed(0)}–${(bucket.max * 100).toFixed(0)}%`;
    }
    const pCount = normalizedPreview?.[index]?.count ?? 0;
    return {
      range,
      name: range,
      min: bucket.min,
      max: bucket.max,
      count: bucket.count,
      fill: getScoreColor(bucket.min),
      preview: isShowingPreview ? pCount : bucket.count,
      previewCount: isShowingPreview ? pCount : undefined,
      remainder: isShowingPreview ? bucket.count - pCount : 0,
    };
  });

  return (
    <ChartContainer config={chartConfig} className="w-full" style={{ height: 200 }}>
      <BarChart data={chartData} stackOffset="none">
        <XAxis dataKey="range" tick={{ fontSize: 10 }} />
        <YAxis hide />
        <ChartTooltip
          cursor={false}
          content={<FacetTooltip nameKey="range" countKey="count" previewKey="previewCount" />}
        />
        <Bar
          dataKey="preview"
          stackId="score"
          radius={isShowingPreview ? [0, 0, 0, 0] : [4, 4, 0, 0]}
          shape={(props: any) => (
            <Rectangle {...props} fill={getScoreColor(props.payload.min)} />
          )}
        />
        <Bar
          dataKey="remainder"
          stackId="score"
          radius={[4, 4, 0, 0]}
          shape={(props: any) => (
            <Rectangle
              {...props}
              fill={getScoreColor(props.payload.min)}
              opacity={isShowingPreview ? 0.3 : 1}
            />
          )}
        />
      </BarChart>
    </ChartContainer>
  );
}

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Brush,
  ResponsiveContainer,
} from "recharts";
import type { HistogramBucket } from "../types";

interface HistogramFacetProps {
  data: HistogramBucket[];
  onRangeChange: (from: number, to: number) => void;
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
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData}>
        <XAxis dataKey="range" tick={{ fontSize: 10 }} />
        <YAxis hide />
        <Tooltip />
        <Bar dataKey="count" fill="hsl(var(--chart-1))" />
        <Brush
          dataKey="range"
          height={20}
          stroke="hsl(var(--border))"
          onChange={handleBrushChange}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

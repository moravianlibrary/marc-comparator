import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { FacetBucket } from "../types";

interface BarFacetProps {
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

export function BarFacet({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: BarFacetProps) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  const chartData = data.map((bucket) => {
    const preview = previewData?.find((p) => p.key === bucket.key);
    return {
      name: bucket.key,
      count: bucket.count,
      preview: preview?.count,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={Math.max(120, data.length * 28)}>
      <BarChart data={chartData} layout="vertical">
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="name"
          width={120}
          tick={{ fontSize: 12 }}
        />
        <Tooltip />
        <Bar
          dataKey="count"
          cursor="pointer"
          onClick={(entry) => onToggle(entry.name)}
          onMouseEnter={(_, index) => {
            const key = chartData[index].name;
            setHoveredKey(key);
            onHover(key);
          }}
          onMouseLeave={() => {
            setHoveredKey(null);
            onLeave();
          }}
        >
          {chartData.map((entry) => (
            <Cell
              key={entry.name}
              fill={
                activeValues.includes(entry.name)
                  ? "hsl(var(--chart-1))"
                  : hoveredKey === entry.name
                    ? "hsl(var(--chart-2))"
                    : "hsl(var(--muted-foreground) / 0.3)"
              }
            />
          ))}
        </Bar>
        {hoveredKey && (
          <Bar dataKey="preview" fill="hsl(var(--chart-2) / 0.3)" />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}

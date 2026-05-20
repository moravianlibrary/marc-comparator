import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { FacetBucket } from "../types";

const COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

interface PieFacetProps {
  data: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

export function PieFacet({
  data,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: PieFacetProps) {
  const chartData = data.map((bucket) => ({
    name: bucket.key,
    value: bucket.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={70}
          cursor="pointer"
          onClick={(entry) => onToggle(entry.name)}
          onMouseEnter={(_, index) => onHover(chartData[index].name)}
          onMouseLeave={onLeave}
        >
          {chartData.map((entry, index) => (
            <Cell
              key={entry.name}
              fill={COLORS[index % COLORS.length]}
              opacity={
                activeValues.length === 0 || activeValues.includes(entry.name)
                  ? 1
                  : 0.3
              }
            />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

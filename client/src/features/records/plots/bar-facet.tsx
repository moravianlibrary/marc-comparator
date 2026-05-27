import { useRef, useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, Cell, LabelList, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { FacetBucket } from "../types";

interface BarFacetProps {
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
  formatLabel?: (key: string) => string;
  /** Width of the Y-axis label column. A number is pixels; a string like "50%" is relative to container width. Default: 100. */
  labelWidth?: number | string;
}

export function BarFacet({
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
  formatLabel,
  labelWidth = 100,
}: BarFacetProps) {
  const { t } = useTranslation();
  const chartConfig = useMemo<ChartConfig>(() => ({
    count: { label: t("common:chart.count"), color: "var(--chart-1)" },
    preview: { label: t("common:chart.preview") },
  }), [t]);

  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setContainerWidth(entry.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const resolvedLabelWidth =
    typeof labelWidth === "string" && labelWidth.endsWith("%")
      ? Math.round((parseFloat(labelWidth) / 100) * containerWidth)
      : (labelWidth as number);

  const isShowingPreview = previewData != null;

  const chartData = data.map((bucket) => {
    const preview = previewData?.find((p) => p.key === bucket.key);
    return {
      key: bucket.key,
      name: formatLabel ? formatLabel(bucket.key) : bucket.key,
      count: bucket.count,
      preview: preview?.count ?? 0,
    };
  });

  return (
    <div ref={containerRef}>
    <ChartContainer
      config={chartConfig}
      className="w-full"
      style={{ height: Math.max(120, data.length * 36) }}
    >
      <BarChart
        accessibilityLayer
        data={chartData}
        layout="vertical"
        margin={{ right: 48 }}
      >
        <YAxis
          dataKey="name"
          type="category"
          tickLine={false}
          tickMargin={8}
          axisLine={false}
          width={resolvedLabelWidth}
          tick={({ x, y, payload, width: tickWidth }: any) => {
            const entry = chartData.find((d) => d.name === payload.value);
            const key = entry?.key ?? payload.value;
            const disabled = isShowingPreview && entry?.preview === 0;
            const w = tickWidth ?? resolvedLabelWidth;
            return (
              <foreignObject x={x - w} y={y - 18} width={w} height={36}>
                <div
                  style={{ cursor: disabled ? "default" : "pointer" }}
                  className="flex items-center justify-end h-full text-xs text-foreground leading-tight pr-2"
                  onClick={(e) => { e.stopPropagation(); if (!disabled) onToggle(key); }}
                  onMouseEnter={() => { if (!disabled) onHover(key); }}
                  onMouseLeave={onLeave}
                >
                  <span className="text-right line-clamp-2">{payload.value}</span>
                </div>
              </foreignObject>
            );
          }}
        />
        <XAxis dataKey="count" type="number" hide />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent indicator="line" />}
        />
        {isShowingPreview && (
          <Bar
            dataKey="preview"
            fill="color-mix(in oklch, var(--muted-foreground) 15%, transparent)"
            radius={4}
            isAnimationActive={false}
          >
            <LabelList
              dataKey="preview"
              position="right"
              offset={8}
              className="fill-muted-foreground"
              fontSize={12}
            />
          </Bar>
        )}
        <Bar
          dataKey="count"
          fill="var(--color-count)"
          radius={4}
          onClick={(entry) => {
            if (isShowingPreview && entry.preview === 0) return;
            onToggle(entry.key);
          }}
          onMouseEnter={(_, index) => onHover(chartData[index].key)}
          onMouseLeave={onLeave}
        >
          {chartData.map((entry) => (
            <Cell
              key={entry.key}
              fill="var(--color-count)"
              cursor={isShowingPreview && entry.preview === 0 ? "default" : "pointer"}
              opacity={isShowingPreview && entry.preview === 0 ? 0.3 : 1}
            />
          ))}
          <LabelList
            dataKey="count"
            position="right"
            offset={8}
            className="fill-foreground"
            fontSize={12}
          />
        </Bar>
      </BarChart>
    </ChartContainer>
    </div>
  );
}

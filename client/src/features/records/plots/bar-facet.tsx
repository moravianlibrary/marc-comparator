import { useRef, useState, useEffect, useMemo, useCallback } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, Cell, LabelList, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { FacetBucket } from "../types";

interface HoveredLabel {
  name: string;
  count: number;
  preview: number;
  rect: DOMRect;
}

function LabelTooltip({ item, config }: { item: HoveredLabel; config: ChartConfig }) {
  const left = item.rect.right;
  const top = item.rect.top + item.rect.height / 2;

  return createPortal(
    <div
      className="pointer-events-none fixed z-50 -translate-y-1/2"
      style={{ left: left + 8, top }}
    >
      <div className="grid min-w-[8rem] items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
        <div className="font-medium">{item.name}</div>
        <div className="grid gap-1.5">
          <div className="flex w-full items-stretch gap-2">
            <div
              className="shrink-0 rounded-[2px] w-1"
              style={{ backgroundColor: "var(--chart-1)" }}
            />
            <div className="flex flex-1 justify-between items-center leading-none">
              <span className="text-muted-foreground">
                {config.count?.label}
              </span>
              <span className="font-mono font-medium text-foreground tabular-nums">
                {item.count.toLocaleString()}
              </span>
            </div>
          </div>
          {item.preview > 0 && (
            <div className="flex w-full items-stretch gap-2">
              <div
                className="shrink-0 rounded-[2px] w-1"
                style={{
                  backgroundColor:
                    "color-mix(in oklch, var(--muted-foreground) 15%, transparent)",
                }}
              />
              <div className="flex flex-1 justify-between items-center leading-none">
                <span className="text-muted-foreground">
                  {config.preview?.label}
                </span>
                <span className="font-mono font-medium text-foreground tabular-nums">
                  {item.preview.toLocaleString()}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

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
  /** Optional map from label key to CSS color value. When present, a small colored circle is rendered before the label text. */
  labelIndicators?: Record<string, string>;
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
  labelIndicators,
}: BarFacetProps) {
  const { t } = useTranslation();
  const chartConfig = useMemo<ChartConfig>(() => ({
    count: { label: t("common:chart.count"), color: "var(--chart-1)" },
    preview: { label: t("common:chart.preview") },
  }), [t]);

  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [hoveredLabel, setHoveredLabel] = useState<HoveredLabel | null>(null);
  const labelRefs = useRef<Map<string, HTMLDivElement>>(new Map());

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

  const handleLabelEnter = useCallback(
    (key: string, entry: (typeof chartData)[0]) => {
      onHover(key);
      const el = labelRefs.current.get(key);
      if (el) {
        setHoveredLabel({
          name: entry.name,
          count: entry.count,
          preview: entry.preview,
          rect: el.getBoundingClientRect(),
        });
      }
    },
    [onHover],
  );

  const handleLabelLeave = useCallback(() => {
    onLeave();
    setHoveredLabel(null);
  }, [onLeave]);

  return (
    <div ref={containerRef}>
    <ChartContainer
      config={chartConfig}
      className="w-full"
      style={{ height: Math.max(120, data.length * 36) }}
    >
      <BarChart
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
              <foreignObject x={x - w} y={y - 18} width={w} height={36} focusable="false">
                <div
                  ref={(el) => { if (el) labelRefs.current.set(key, el); }}
                  style={{ cursor: disabled ? "default" : "pointer" }}
                  className="flex items-center justify-end h-full text-xs text-foreground leading-tight pr-2 outline-none"
                  onClick={(e) => { e.stopPropagation(); if (!disabled) onToggle(key); }}
                  onMouseEnter={() => { if (!disabled && entry) handleLabelEnter(key, entry); }}
                  onMouseLeave={handleLabelLeave}
                >
                  {labelIndicators?.[key] && (
                    <span
                      className="inline-block h-2 w-2 rounded-full flex-shrink-0 mr-1.5"
                      style={{ backgroundColor: labelIndicators[key] }}
                    />
                  )}
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
    {hoveredLabel && <LabelTooltip item={hoveredLabel} config={chartConfig} />}
    </div>
  );
}

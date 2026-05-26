import { useState, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import type { FacetBucket } from "../types";

interface HoveredSegment {
  facetField: string;
  key: string;
  name: string;
  count: number;
  preview?: number;
  color: string;
  rect: DOMRect;
}

function SegmentTooltip({ segment }: { segment: HoveredSegment }) {
  const { t } = useTranslation();
  const left = segment.rect.left + segment.rect.width / 2;
  const top = segment.rect.top;

  return createPortal(
    <div
      className="pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-full"
      style={{ left, top: top - 8 }}
    >
      <div className="grid min-w-[8rem] items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
        <div className="font-medium">{segment.name}</div>
        <div className="grid gap-1.5">
          <div className="flex w-full items-stretch gap-2">
            <div
              className="shrink-0 rounded-[2px] w-1"
              style={{ backgroundColor: segment.color }}
            />
            <div className="flex flex-1 justify-between items-center leading-none">
              <span className="text-muted-foreground">
                {t("common:chart.count")}
              </span>
              <span className="font-mono font-medium text-foreground tabular-nums">
                {segment.count.toLocaleString()}
              </span>
            </div>
          </div>
          {segment.preview != null && segment.preview > 0 && (
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
                  {t("common:chart.preview")}
                </span>
                <span className="font-mono font-medium text-foreground tabular-nums">
                  {segment.preview.toLocaleString()}
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

interface StatusSegment {
  key: string;
  color: string;
}

interface StatusRow {
  label: string;
  facetField: string;
  buckets: FacetBucket[];
  previewBuckets?: FacetBucket[];
  segments: StatusSegment[];
}

interface StatusTripleFacetProps {
  rows: StatusRow[];
  activeValues: Record<string, string[]>;
  onToggle: (facetField: string, value: string) => void;
  onHover: (facetField: string, value: string) => void;
  onLeave: () => void;
}

export function StatusTripleFacet({
  rows,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: StatusTripleFacetProps) {
  const { t } = useTranslation("records");
  const [hovered, setHovered] = useState<HoveredSegment | null>(null);
  const buttonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const handleMouseEnter = useCallback(
    (facetField: string, seg: StatusSegment, count: number, previewCount: number | undefined) => {
      onHover(facetField, seg.key);
      const el = buttonRefs.current.get(`${facetField}-${seg.key}`);
      if (el) {
        setHovered({
          facetField,
          key: seg.key,
          name: t(`state.${seg.key}`),
          count,
          preview: previewCount,
          color: seg.color,
          rect: el.getBoundingClientRect(),
        });
      }
    },
    [onHover, t],
  );

  const handleMouseLeave = useCallback(() => {
    onLeave();
    setHovered(null);
  }, [onLeave]);

  return (
    <div className="space-y-4">
      {rows.map((row) => {
        const total = row.buckets.reduce((sum, b) => sum + b.count, 0);
        const active = activeValues[row.facetField] ?? [];
        const isShowingPreview = row.previewBuckets != null;

        return (
          <div key={row.facetField} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{row.label}</span>
              <span className="text-muted-foreground text-xs">
                {total.toLocaleString("cs-CZ")}
              </span>
            </div>
            <div className="flex h-8 w-full rounded-md overflow-hidden text-xs font-semibold cursor-pointer">
              {row.segments.map((seg) => {
                const bucket = row.buckets.find((b) => b.key === seg.key);
                const count = bucket?.count ?? 0;
                if (count === 0) return null;
                const percent = total > 0 ? Math.round((count / total) * 100) : 0;
                const previewCount = row.previewBuckets?.find((b) => b.key === seg.key)?.count ?? 0;
                const previewPercent = count > 0 ? Math.round((previewCount / count) * 100) : 0;

                return (
                  <button
                    key={seg.key}
                    ref={(el) => {
                      if (el) buttonRefs.current.set(`${row.facetField}-${seg.key}`, el);
                    }}
                    className="relative flex items-center justify-center px-2 overflow-hidden"
                    style={{ width: `${percent}%`, color: "black" }}
                    onClick={() => {
                      if (isShowingPreview && previewCount === 0) return;
                      onToggle(row.facetField, seg.key);
                    }}
                    onMouseEnter={() =>
                      handleMouseEnter(
                        row.facetField,
                        seg,
                        count,
                        isShowingPreview ? previewCount : undefined,
                      )
                    }
                    onMouseLeave={handleMouseLeave}
                  >
                    <div
                      className="absolute inset-0"
                      style={{
                        backgroundColor: seg.color,
                        opacity: (() => {
                          const isSiblingHovered =
                            hovered != null &&
                            hovered.facetField === row.facetField &&
                            hovered.key !== seg.key;
                          if (isShowingPreview) {
                            return isSiblingHovered ? 0.15 : 0.3;
                          }
                          if (isSiblingHovered) {
                            return 0.3;
                          }
                          if (active.length > 0 && !active.includes(seg.key)) {
                            return 0.3;
                          }
                          return 1;
                        })(),
                      }}
                    />
                    {isShowingPreview && previewPercent > 0 && (
                      <div
                        className="absolute inset-y-0 left-0"
                        style={{
                          width: `${previewPercent}%`,
                          backgroundColor: seg.color,
                        }}
                      />
                    )}
                    {percent >= 12 && (
                      <span className="relative z-10">
                        {t(`state.${seg.key}`)} {percent}%
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
      {hovered && <SegmentTooltip segment={hovered} />}
    </div>
  );
}

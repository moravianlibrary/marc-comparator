import { useTranslation } from "react-i18next";
import type { FacetBucket } from "../types";

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
                    className="relative flex items-center justify-center px-2 overflow-hidden"
                    style={{ width: `${percent}%`, color: "black" }}
                    onClick={() => {
                      if (isShowingPreview && previewCount === 0) return;
                      onToggle(row.facetField, seg.key);
                    }}
                    onMouseEnter={() => onHover(row.facetField, seg.key)}
                    onMouseLeave={onLeave}
                  >
                    <div
                      className="absolute inset-0"
                      style={{
                        backgroundColor: seg.color,
                        opacity:
                          active.length === 0 || active.includes(seg.key)
                            ? (isShowingPreview ? 0.3 : 1)
                            : 0.3,
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
    </div>
  );
}

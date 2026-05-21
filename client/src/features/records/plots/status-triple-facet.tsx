import { useTranslation } from "react-i18next";
import type { FacetBucket } from "../types";

interface StatusRow {
  label: string;
  facetField: string;
  buckets: FacetBucket[];
  previewBuckets?: FacetBucket[];
  positiveKey: string;
  negativeKey: string;
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
        const positive = row.buckets.find((b) => b.key === row.positiveKey);
        const negative = row.buckets.find((b) => b.key === row.negativeKey);
        const positiveCount = positive?.count ?? 0;
        const negativeCount = negative?.count ?? 0;
        const total = positiveCount + negativeCount;
        const positivePercent = total > 0 ? Math.round((positiveCount / total) * 100) : 0;
        const negativePercent = 100 - positivePercent;
        const active = activeValues[row.facetField] ?? [];

        const isShowingPreview = row.previewBuckets != null;
        const previewPositive = row.previewBuckets?.find((b) => b.key === row.positiveKey)?.count ?? 0;
        const previewNegative = row.previewBuckets?.find((b) => b.key === row.negativeKey)?.count ?? 0;
        const previewPositivePercent = positiveCount > 0 ? Math.round((previewPositive / positiveCount) * 100) : 0;
        const previewNegativePercent = negativeCount > 0 ? Math.round((previewNegative / negativeCount) * 100) : 0;

        return (
          <div key={row.facetField} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{row.label}</span>
              <span className="text-muted-foreground text-xs">
                {total.toLocaleString("cs-CZ")}
              </span>
            </div>
            <div className="flex h-8 w-full rounded-md overflow-hidden text-xs font-semibold cursor-pointer">
              {positiveCount > 0 && (
                <button
                  className="relative flex items-center justify-center px-2 overflow-hidden"
                  style={{
                    width: `${positivePercent}%`,
                    color: "black",
                  }}
                  onClick={() => {
                    if (isShowingPreview && previewPositive === 0) return;
                    onToggle(row.facetField, row.positiveKey);
                  }}
                  onMouseEnter={() => onHover(row.facetField, row.positiveKey)}
                  onMouseLeave={onLeave}
                >
                  <div
                    className="absolute inset-0"
                    style={{
                      backgroundColor: "var(--chart-1)",
                      opacity:
                        active.length === 0 || active.includes(row.positiveKey)
                          ? (isShowingPreview ? 0.3 : 1)
                          : 0.3,
                    }}
                  />
                  {isShowingPreview && previewPositivePercent > 0 && (
                    <div
                      className="absolute inset-y-0 left-0"
                      style={{
                        width: `${previewPositivePercent}%`,
                        backgroundColor: "var(--chart-1)",
                      }}
                    />
                  )}
                  {positivePercent >= 15 && (
                    <span className="relative z-10">
                      {t(`state.${row.positiveKey}`)} {positivePercent}%
                    </span>
                  )}
                </button>
              )}
              {negativeCount > 0 && (
                <button
                  className="relative flex items-center justify-center px-2 overflow-hidden"
                  style={{
                    width: `${negativePercent}%`,
                    color: "black",
                  }}
                  onClick={() => {
                    if (isShowingPreview && previewNegative === 0) return;
                    onToggle(row.facetField, row.negativeKey);
                  }}
                  onMouseEnter={() => onHover(row.facetField, row.negativeKey)}
                  onMouseLeave={onLeave}
                >
                  <div
                    className="absolute inset-0"
                    style={{
                      backgroundColor: "var(--chart-4)",
                      opacity:
                        active.length === 0 || active.includes(row.negativeKey)
                          ? (isShowingPreview ? 0.3 : 1)
                          : 0.3,
                    }}
                  />
                  {isShowingPreview && previewNegativePercent > 0 && (
                    <div
                      className="absolute inset-y-0 left-0"
                      style={{
                        width: `${previewNegativePercent}%`,
                        backgroundColor: "var(--chart-4)",
                      }}
                    />
                  )}
                  {negativePercent >= 15 && (
                    <span className="relative z-10">
                      {t(`state.${row.negativeKey}`)} {negativePercent}%
                    </span>
                  )}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

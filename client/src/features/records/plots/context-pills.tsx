import { cn } from "@/lib/utils";
import type { FacetBucket } from "../types";

interface ContextPillsProps {
  buckets: FacetBucket[];
  previewBuckets?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

export function ContextPills({
  buckets,
  previewBuckets,
  activeValues,
  onToggle,
  onHover,
  onLeave,
}: ContextPillsProps) {
  const isShowingPreview = previewBuckets && previewBuckets.length > 0;

  return (
    <div className="flex flex-wrap gap-1.5">
      {buckets.map((bucket) => {
        const isActive = activeValues.includes(bucket.key);
        const hasActiveFilter = activeValues.length > 0;
        const previewBucket = previewBuckets?.find(
          (p) => p.key === bucket.key,
        );
        const previewCount = previewBucket?.count ?? 0;
        const isDisabled = isShowingPreview && !isActive && previewCount === 0;
        return (
          <button
            key={bucket.key}
            disabled={isDisabled}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-sm font-medium transition-colors",
              isDisabled
                ? "bg-muted text-muted-foreground opacity-30 cursor-not-allowed"
                : isActive
                  ? "bg-primary text-primary-foreground"
                  : hasActiveFilter
                    ? "bg-muted text-muted-foreground opacity-50"
                    : "bg-muted text-foreground hover:bg-accent",
            )}
            onClick={() => onToggle(bucket.key)}
            onMouseEnter={() => onHover(bucket.key)}
            onMouseLeave={onLeave}
          >
            <span>{bucket.key}</span>
            <span
              className={cn(
                "text-xs tabular-nums",
                isActive
                  ? "text-primary-foreground/70"
                  : "text-muted-foreground",
              )}
            >
              {bucket.count.toLocaleString("cs-CZ")}
            </span>
            {isShowingPreview && !isActive && (
              <span className="text-xs tabular-nums text-chart-2">
                {(previewBucket?.count ?? 0).toLocaleString("cs-CZ")}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

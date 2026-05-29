import { cn } from "@/lib/utils";
import type { FacetBucket } from "../types";

interface ContextPillsProps {
  buckets: FacetBucket[];
  previewBuckets?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
  formatLabel?: (key: string) => string;
}

export function ContextPills({
  buckets,
  previewBuckets,
  activeValues,
  onToggle,
  onHover,
  onLeave,
  formatLabel,
}: ContextPillsProps) {
  const isShowingPreview = previewBuckets != null;

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
        const showPreviewCount = isShowingPreview && !isActive;
        return (
          <button
            key={bucket.key}
            disabled={isDisabled}
            className={cn(
              "relative inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-sm font-medium transition-colors",
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
            <span>{formatLabel ? formatLabel(bucket.key) : bucket.key}</span>
            <span
              className={cn(
                "text-xs tabular-nums rounded px-1 py-0.5",
                isActive
                  ? "bg-primary-foreground/20 text-primary-foreground/70"
                  : "bg-foreground text-background",
              )}
            >
              {bucket.count.toLocaleString("cs-CZ")}
            </span>
            <span
              className="absolute -top-2 -right-2 text-[10px] tabular-nums leading-none rounded-full bg-primary text-primary-foreground px-1 py-0.5 min-w-[1.25rem] text-center transition-all duration-300 origin-center"
              style={{
                opacity: showPreviewCount ? 1 : 0,
                transform: showPreviewCount ? "scale(1)" : "scale(0)",
              }}
            >
              {previewCount.toLocaleString("cs-CZ")}
            </span>
          </button>
        );
      })}
    </div>
  );
}

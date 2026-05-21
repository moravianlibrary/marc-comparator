import { cn } from "@/lib/utils";
import { usePrefetchFacetPreview } from "./use-facets";
import type { FacetBucket } from "../types";

interface PillGroupProps {
  label: string;
  facetField: string;
  buckets: FacetBucket[];
  previewBuckets?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

interface ContextPillsProps {
  groups: PillGroupProps[];
}

export function ContextPills({ groups }: ContextPillsProps) {
  const prefetch = usePrefetchFacetPreview();

  return (
    <div className="flex flex-wrap gap-x-8 gap-y-4">
      {groups.map((group) => (
        <div
          key={group.facetField}
          className="space-y-1.5"
          onMouseEnter={() => prefetch(group.facetField)}
        >
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            {group.label}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {group.buckets.map((bucket) => {
              const isActive = group.activeValues.includes(bucket.key);
              const hasActiveFilter = group.activeValues.length > 0;
              const previewBucket = group.previewBuckets?.find(
                (p) => p.key === bucket.key,
              );
              const isShowingPreview =
                group.previewBuckets && group.previewBuckets.length > 0;
              const displayCount = isShowingPreview
                ? (previewBucket?.count ?? 0)
                : bucket.count;

              return (
                <button
                  key={bucket.key}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : hasActiveFilter
                        ? "bg-muted text-muted-foreground opacity-50"
                        : "bg-muted text-foreground hover:bg-accent",
                  )}
                  onClick={() => group.onToggle(bucket.key)}
                  onMouseEnter={() => group.onHover(bucket.key)}
                  onMouseLeave={group.onLeave}
                >
                  <span>{bucket.key}</span>
                  <span
                    className={cn(
                      "text-xs tabular-nums",
                      isActive
                        ? "text-primary-foreground/70"
                        : "text-muted-foreground",
                      isShowingPreview && !isActive && "text-chart-2",
                    )}
                  >
                    {displayCount.toLocaleString("cs-CZ")}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePrefetchFacetPreview } from "./use-facets";
import type { FacetBucket } from "../types";

export interface FacetChildProps {
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
  formatLabel?: (key: string) => string;
}

interface FacetChartProps {
  title: string;
  /** The backend facet field name (used for preview prefetch). */
  facetField: string;
  data: FacetBucket[];
  previewData?: FacetBucket[];
  activeValues: string[];
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
  formatLabel?: (key: string) => string;
  headerRight?: React.ReactNode;
  className?: string;
  contentClassName?: string;
  children: (props: FacetChildProps) => React.ReactNode;
}

export function FacetChart({
  title,
  facetField,
  data,
  previewData,
  activeValues,
  onToggle,
  onHover,
  onLeave,
  formatLabel,
  headerRight,
  className,
  contentClassName,
  children,
}: FacetChartProps) {
  const prefetch = usePrefetchFacetPreview();
  const hasActive = activeValues.length > 0;

  return (
    <Card
      className={cn(hasActive && "ring-2 ring-primary/30", className)}
      onMouseEnter={() => prefetch(facetField)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            {title}
            {hasActive && (
              <span className="inline-block h-2 w-2 rounded-full bg-primary" />
            )}
          </CardTitle>
          {headerRight}
        </div>
      </CardHeader>
      <CardContent className={contentClassName}>
        {children({
          data,
          previewData,
          activeValues,
          onToggle,
          onHover,
          onLeave,
          formatLabel,
        })}
      </CardContent>
    </Card>
  );
}

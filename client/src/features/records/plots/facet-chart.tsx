import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePrefetchFacetPreview } from "./use-facets";
import type { FacetBucket } from "../types";

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
  children: (props: {
    data: FacetBucket[];
    previewData?: FacetBucket[];
    activeValues: string[];
    onToggle: (value: string) => void;
    onHover: (value: string) => void;
    onLeave: () => void;
  }) => React.ReactNode;
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
  children,
}: FacetChartProps) {
  const prefetch = usePrefetchFacetPreview();

  return (
    <Card onMouseEnter={() => prefetch(facetField)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {children({
          data,
          previewData,
          activeValues,
          onToggle,
          onHover,
          onLeave,
        })}
      </CardContent>
    </Card>
  );
}

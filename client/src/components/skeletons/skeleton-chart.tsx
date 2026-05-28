import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

// Varying bar widths for visual interest
const BAR_WIDTHS = ["w-[85%]", "w-[60%]", "w-[75%]", "w-[45%]", "w-[90%]", "w-[55%]", "w-[70%]", "w-[40%]"];

// Varying histogram bar heights (out of 200px container)
const HISTOGRAM_HEIGHTS = [
  20, 45, 80, 120, 160, 180, 190, 175, 155, 130,
  100, 75, 55, 40, 30, 50, 70, 90, 60, 35,
];

interface SkeletonBarChartProps {
  bars?: number;
  className?: string;
}

export function SkeletonBarChart({ bars = 5, className }: SkeletonBarChartProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {Array.from({ length: bars }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-4 w-24 flex-none" />
              <Skeleton className={cn("h-4", BAR_WIDTHS[i % BAR_WIDTHS.length])} />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface SkeletonDonutChartProps {
  className?: string;
}

export function SkeletonDonutChart({ className }: SkeletonDonutChartProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6 justify-center">
          {/* Donut circle */}
          <Skeleton className="h-[180px] w-[180px] rounded-full flex-none" />
          {/* Legend */}
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2">
                <Skeleton className="h-3 w-3 rounded-full flex-none" />
                <Skeleton className="h-3 w-20" />
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface SkeletonHistogramProps {
  className?: string;
}

export function SkeletonHistogram({ className }: SkeletonHistogramProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-[2px] h-[200px]">
          {HISTOGRAM_HEIGHTS.map((height, i) => (
            <Skeleton
              key={i}
              className="flex-1"
              style={{ height: `${height}px` }}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface SkeletonStackedBarProps {
  className?: string;
}

export function SkeletonStackedBar({ className }: SkeletonStackedBarProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-full" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface SkeletonRadialChartProps {
  className?: string;
  size?: number;
}

export function SkeletonRadialChart({ className, size = 180 }: SkeletonRadialChartProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6 justify-center">
          {/* Radial circle */}
          <Skeleton
            className="rounded-full flex-none"
            style={{ width: size, height: size }}
          />
          {/* Legend */}
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2">
                <Skeleton className="h-3 w-3 rounded-full flex-none" />
                <Skeleton className="h-3 w-20" />
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

import { Skeleton } from "@/components/ui/skeleton";
import {
  SkeletonBarChart,
  SkeletonDonutChart,
  SkeletonHistogram,
  SkeletonRadialChart,
  SkeletonStackedBar,
} from "./skeleton-chart";

export function SkeletonRecordsSection() {
  return (
    <section className="space-y-2">
      <Skeleton className="h-4 w-32" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SkeletonStackedBar />
        <SkeletonBarChart bars={4} />
        <SkeletonDonutChart />
      </div>
    </section>
  );
}

export function SkeletonComparisonSection() {
  return (
    <section className="space-y-2">
      <Skeleton className="h-4 w-36" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SkeletonRadialChart size={160} />
        <SkeletonHistogram />
        <SkeletonBarChart bars={6} />
      </div>
    </section>
  );
}

export function SkeletonValidationSection() {
  return (
    <section className="space-y-2">
      <Skeleton className="h-4 w-36" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SkeletonRadialChart />
        <SkeletonBarChart bars={5} className="md:col-span-2" />
      </div>
    </section>
  );
}

import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonTableProps {
  rows?: number;
  columns?: number;
}

export function SkeletonTable({ rows = 5, columns = 4 }: SkeletonTableProps) {
  return (
    <div className="rounded-md border overflow-hidden">
      {/* Header row */}
      <div className="flex gap-2 px-3 py-2 bg-muted/50 border-b">
        <Skeleton className="h-4 max-w-[80px] w-full flex-none" />
        {Array.from({ length: columns - 1 }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>

      {/* Data rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={rowIdx}
          className="flex gap-2 px-3 py-2 border-b last:border-b-0"
        >
          <Skeleton className="h-4 max-w-[80px] w-full flex-none" />
          {Array.from({ length: columns - 1 }).map((_, colIdx) => (
            <Skeleton key={colIdx} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

// Varying subfield widths per row index for visual interest
const SUBFIELD_WIDTHS = [
  ["w-[60%]", "w-[30%]"],
  ["w-[80%]"],
  ["w-[40%]", "w-[50%]"],
  ["w-[70%]"],
  ["w-[55%]", "w-[25%]"],
  ["w-[90%]"],
  ["w-[45%]", "w-[40%]"],
  ["w-[65%]"],
  ["w-[35%]", "w-[45%]"],
  ["w-[75%]"],
  ["w-[50%]", "w-[30%]"],
  ["w-[85%]"],
];

interface SkeletonMarcTableProps {
  rows?: number;
  showAnnotationColumn?: boolean;
}

export function SkeletonMarcTable({
  rows = 12,
  showAnnotationColumn = false,
}: SkeletonMarcTableProps) {
  return (
    <div className="rounded-md border overflow-hidden">
      {Array.from({ length: rows }).map((_, rowIdx) => {
        const widths = SUBFIELD_WIDTHS[rowIdx % SUBFIELD_WIDTHS.length];
        const striped = rowIdx % 2 === 1;

        return (
          <div
            key={rowIdx}
            className={cn("flex border-b last:border-b-0", striped && "bg-muted/50")}
          >
            {/* Tag + indicators column (120px) */}
            <div className="flex w-[120px] flex-none items-start gap-2 px-3 py-1.5">
              <Skeleton className="h-4 w-9" />
              <Skeleton className="h-4 w-5" />
            </div>

            {/* Subfields content column */}
            <div
              className={cn(
                "flex flex-col gap-1 px-3 py-1.5",
                showAnnotationColumn ? "w-[35%] flex-none" : "flex-1",
              )}
            >
              {widths!.map((w, i) => (
                <div key={i} className="flex gap-2">
                  <Skeleton className="h-4 w-5 flex-none" />
                  <Skeleton className={cn("h-4", w)} />
                </div>
              ))}
            </div>

            {/* Annotation column */}
            {showAnnotationColumn && (
              <div className="flex-1 border-l px-3 py-1.5">
                <Skeleton className="h-4 w-[60%]" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

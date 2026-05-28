import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonFormProps {
  fields?: number;
}

export function SkeletonForm({ fields = 5 }: SkeletonFormProps) {
  return (
    <div className="space-y-4">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          {/* Label */}
          <Skeleton className="h-4 w-32" />
          {/* Input */}
          <Skeleton className="h-10 w-full" />
        </div>
      ))}

      {/* Submit button */}
      <div className="pt-2">
        <Skeleton className="h-10 w-28" />
      </div>
    </div>
  );
}

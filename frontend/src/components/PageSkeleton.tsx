import { Skeleton } from "@/components/ui/skeleton";

interface PageSkeletonProps {
  /** Number of content blocks to render. */
  blocks?: number;
}

/** Generic page-level loading placeholder. */
export function PageSkeleton({ blocks = 3 }: PageSkeletonProps) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Chargement en cours">
      <Skeleton className="h-8 w-1/3" />
      {Array.from({ length: blocks }, (_, index) => (
        <Skeleton key={index} className="h-32 w-full" data-testid="page-skeleton-block" />
      ))}
    </div>
  );
}

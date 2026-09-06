import { Card } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

export function IncidentDetailSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true">
      <span className="sr-only">Loading incident details</span>
      <Skeleton className="h-6 w-40" />
      <Skeleton className="h-8 w-2/3" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(20rem,1fr)]">
        <Card className="p-5">
          <Skeleton className="h-40 w-full" />
        </Card>
        <Card className="p-5">
          <Skeleton className="h-40 w-full" />
        </Card>
      </div>
    </div>
  );
}

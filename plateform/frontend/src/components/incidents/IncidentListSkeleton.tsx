import { Card } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

export function IncidentListSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading incidents</span>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Card key={index} className="p-5">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="mt-5 h-8 w-16" />
            <Skeleton className="mt-3 h-4 w-32" />
          </Card>
        ))}
      </div>
      <Card className="p-5">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="mt-3 h-10 w-full" />
      </Card>
      <Card className="p-5">
        <Skeleton className="h-48 w-full" />
      </Card>
    </div>
  );
}

import { Clock3 } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-2xl items-center justify-center">
      <div className="card w-full px-8 py-14 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-light text-teal">
          <Clock3 size={22} aria-hidden="true" />
        </div>
        <h2 className="text-xl font-semibold text-ink">{title}</h2>
        <p className="mt-2 text-sm text-ink-muted">{description}</p>
        <p className="mt-6 text-sm font-medium text-teal">Coming in the next step</p>
      </div>
    </div>
  );
}

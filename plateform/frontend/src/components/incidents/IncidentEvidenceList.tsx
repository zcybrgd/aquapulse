import type { EvidenceItem } from "../../types/incidents";
import { Card } from "../ui/Card";

interface IncidentEvidenceListProps {
  evidence: EvidenceItem[];
}

export function IncidentEvidenceList({ evidence }: IncidentEvidenceListProps) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Evidence</h3>
      <p className="mt-0.5 text-sm text-ink-muted">Material used during the investigation</p>
      <ul className="mt-4 space-y-3">
        {evidence.map((item) => (
          <li key={item.id} className="rounded-2xl border border-line px-3 py-3">
            <p className="text-sm font-medium text-ink">{item.title}</p>
            <p className="mt-1 text-sm text-ink-muted">{item.detail}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

import { Link } from "react-router-dom";

import { formatDateTime } from "../../lib/format";
import type { AgentFindingRecord } from "../../types/integrations";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

const severityStyle: Record<number, string> = {
  1: "bg-page text-ink-muted",
  2: "bg-warning/10 text-warning",
  3: "bg-critical/10 text-critical",
};

function FindingAction({ item }: { item: AgentFindingRecord }) {
  if (item.mapped_detection_id) {
    return (
      <Link
        to={`/detections/${encodeURIComponent(item.mapped_detection_id)}`}
        className="relative z-10 text-sm font-medium text-teal hover:underline"
      >
        Open detection
      </Link>
    );
  }
  return (
    <Link
      to={`/detections/findings/${encodeURIComponent(item.id)}`}
      className="relative z-10 text-sm font-medium text-teal hover:underline"
    >
      Open result
    </Link>
  );
}

export function AgentFindingTable({ items }: { items: AgentFindingRecord[] }) {
  return (
    <Card className="hidden min-w-0 overflow-hidden xl:block">
      <table className="w-full table-fixed border-collapse text-left text-sm">
        <thead className="bg-page text-xs font-medium uppercase tracking-wide text-ink-muted">
          <tr>
            <th className="w-[16%] px-4 py-3">Cluster</th>
            <th className="w-[20%] px-4 py-3">Classification</th>
            <th className="w-[16%] px-4 py-3">Severity</th>
            <th className="w-[10%] px-4 py-3">Confidence</th>
            <th className="w-[12%] px-4 py-3">Mapping</th>
            <th className="w-[14%] px-4 py-3">Assessed</th>
            <th className="w-[12%] px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t border-line">
              <td className="px-4 py-3 align-top">
                <p className="font-medium text-ink">{item.external_cluster_id ?? "Unmapped cluster"}</p>
                <p className="mt-0.5 truncate text-xs text-ink-muted">{item.external_anomaly_id}</p>
              </td>
              <td className="px-4 py-3 align-top text-ink">{item.classification_label}</td>
              <td className="px-4 py-3 align-top">
                <Badge className={severityStyle[item.severity_tier] ?? "bg-page text-ink-muted"}>
                  {item.severity_label}
                </Badge>
              </td>
              <td className="px-4 py-3 align-top text-ink">{item.confidence_score.toFixed(2)}</td>
              <td className="px-4 py-3 align-top text-ink-muted">
                {item.mapped_detection_id ?? item.mapping_status}
              </td>
              <td className="px-4 py-3 align-top text-ink-muted">{formatDateTime(item.created_at)}</td>
              <td className="px-4 py-3 align-top">
                <FindingAction item={item} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export function AgentFindingCardList({ items }: { items: AgentFindingRecord[] }) {
  return (
    <ul className="space-y-3 xl:hidden">
      {items.map((item) => (
        <li key={item.id}>
          <div className="card min-w-0 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-ink">{item.external_cluster_id ?? item.external_anomaly_id}</p>
              <Badge className={severityStyle[item.severity_tier] ?? "bg-page text-ink-muted"}>
                {item.severity_label}
              </Badge>
            </div>
            <p className="mt-2 text-sm text-ink">{item.classification_label}</p>
            <p className="mt-2 text-sm text-ink-muted">{item.operator_justification}</p>
            <div className="mt-3">
              <FindingAction item={item} />
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

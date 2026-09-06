import { Link, useLocation, useNavigate } from "react-router-dom";

import { formatDateTime } from "../../lib/format";
import { isTerminalDetection, queuePrimaryAction, RULE_LABELS, scorePercent } from "../../lib/detections";
import type { DetectionSummary } from "../../types/detections";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { DetectionPriorityBadge } from "./DetectionPriorityBadge";
import { DetectionStatusBadge } from "./DetectionStatusBadge";

function detailsPath(id: string, search: string): string {
  return `/detections/${encodeURIComponent(id)}${search}`;
}

function ActionLink({
  item,
  search,
  busy,
  onStartReview,
}: {
  item: DetectionSummary;
  search: string;
  busy?: boolean;
  onStartReview?: (id: string) => void;
}) {
  const action = queuePrimaryAction(item);
  if (action.kind === "start_review") {
    return (
      <Button
        variant="secondary"
        className="!px-2.5 !py-1 text-xs"
        disabled={busy}
        onClick={(event) => {
          event.stopPropagation();
          onStartReview?.(item.id);
        }}
      >
        {action.label}
      </Button>
    );
  }
  if (action.kind === "view_incident" && item.incident_id) {
    return (
      <Link
        to={`/incidents/${encodeURIComponent(item.incident_id)}`}
        className="relative z-10 text-sm font-medium text-teal hover:underline"
        onClick={(event) => event.stopPropagation()}
      >
        {action.label}
      </Link>
    );
  }
  if (action.kind === "view_merged" && item.merged_into_detection_id) {
    return (
      <Link
        to={detailsPath(item.merged_into_detection_id, search)}
        className="relative z-10 text-sm font-medium text-teal hover:underline"
        onClick={(event) => event.stopPropagation()}
      >
        {action.label}
      </Link>
    );
  }
  return (
    <Link
      to={detailsPath(item.id, search)}
      className="relative z-10 text-sm font-medium text-teal hover:underline"
      onClick={(event) => event.stopPropagation()}
    >
      {action.label}
    </Link>
  );
}

export function DetectionTable({
  items,
  busy,
  onStartReview,
}: {
  items: DetectionSummary[];
  busy?: boolean;
  onStartReview?: (id: string) => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Card className="hidden min-w-0 overflow-hidden xl:block">
      <table className="w-full table-fixed border-collapse text-left text-sm">
        <thead className="bg-page text-xs font-medium uppercase tracking-wide text-ink-muted">
          <tr>
            <th className="w-[12%] px-4 py-3">Detection</th>
            <th className="w-[9%] px-4 py-3">Screening priority</th>
            <th className="w-[18%] px-4 py-3">Trigger</th>
            <th className="w-[11%] px-4 py-3">Sensor</th>
            <th className="w-[10%] px-4 py-3">Zone</th>
            <th className="w-[7%] px-4 py-3">Score</th>
            <th className="w-[10%] px-4 py-3">Status</th>
            <th className="w-[11%] px-4 py-3">Updated</th>
            <th className="w-[12%] px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className={`cursor-pointer border-t border-line transition-colors hover:bg-teal-light/40 ${
                isTerminalDetection(item.status) ? "bg-page/70 text-ink-muted" : ""
              }`}
              onClick={() => navigate(detailsPath(item.id, location.search))}
            >
              <td className="px-4 py-3 align-top">
                <p className="font-medium text-ink">{item.detection_number}</p>
                <p className="mt-0.5 truncate text-xs text-ink-muted">
                  {RULE_LABELS[item.rule_code] ?? item.rule_name}
                </p>
                {item.reviewed_by ? (
                  <p className="mt-0.5 truncate text-xs text-ink-muted">{item.reviewed_by}</p>
                ) : null}
              </td>
              <td className="px-4 py-3 align-top">
                <DetectionPriorityBadge priority={item.priority} />
                {item.awaiting_agent_investigation ? (
                  <p className="mt-1 text-xs text-ink-muted">Awaiting agent investigation</p>
                ) : null}
                {item.has_agent_finding ? (
                  <p className="mt-1 text-xs text-teal">Agent-assessed</p>
                ) : null}
              </td>
              <td className="px-4 py-3 align-top">
                <p className="line-clamp-2 text-ink">{item.trigger_reason}</p>
              </td>
              <td className="px-4 py-3 align-top">
                <p className="truncate text-ink">{item.sensor_id}</p>
              </td>
              <td className="px-4 py-3 align-top">
                <p className="truncate text-ink">{item.zone}</p>
              </td>
              <td className="px-4 py-3 align-top text-ink">{scorePercent(item.anomaly_score)}</td>
              <td className="px-4 py-3 align-top">
                <DetectionStatusBadge status={item.status} />
              </td>
              <td className="px-4 py-3 align-top text-ink-muted">
                {formatDateTime(item.updated_at ?? item.detected_at)}
              </td>
              <td className="px-4 py-3 align-top">
                <ActionLink item={item} search={location.search} busy={busy} onStartReview={onStartReview} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export function DetectionCardList({
  items,
  busy,
  onStartReview,
}: {
  items: DetectionSummary[];
  busy?: boolean;
  onStartReview?: (id: string) => void;
}) {
  const location = useLocation();

  return (
    <ul className="space-y-3 xl:hidden">
      {items.map((item) => (
        <li key={item.id}>
          <div
            className={`card min-w-0 p-4 ${isTerminalDetection(item.status) ? "bg-page/80" : ""}`}
          >
            <Link to={detailsPath(item.id, location.search)} className="block hover:border-teal/30">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-ink">{item.detection_number}</p>
                <DetectionPriorityBadge priority={item.priority} />
                <DetectionStatusBadge status={item.status} />
                {item.awaiting_agent_investigation ? (
                  <span className="text-xs text-ink-muted">Awaiting agent investigation</span>
                ) : null}
                {item.has_agent_finding ? <span className="text-xs text-teal">Agent-assessed</span> : null}
              </div>
              <p className="mt-2 text-sm text-ink">{item.trigger_reason}</p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-muted">
                <div>
                  <dt>Sensor</dt>
                  <dd className="mt-0.5 text-ink">{item.sensor_id}</dd>
                </div>
                <div>
                  <dt>Zone</dt>
                  <dd className="mt-0.5 text-ink">{item.zone}</dd>
                </div>
                <div>
                  <dt>Reviewed by</dt>
                  <dd className="mt-0.5 text-ink">{item.reviewed_by ?? "—"}</dd>
                </div>
                <div>
                  <dt>Updated</dt>
                  <dd className="mt-0.5 text-ink">{formatDateTime(item.updated_at ?? item.detected_at)}</dd>
                </div>
              </dl>
            </Link>
            <div className="mt-3">
              <ActionLink item={item} search={location.search} busy={busy} onStartReview={onStartReview} />
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

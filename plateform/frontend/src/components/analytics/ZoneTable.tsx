import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { downloadTextFile, zoneRowsToCsv } from "../../lib/analytics";
import { formatNumber } from "../../lib/format";
import type { AnalyticsZonesResponse, ZoneAnalyticsRow } from "../../types/analytics";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

type SortKey = keyof Pick<
  ZoneAnalyticsRow,
  | "zone"
  | "reporting_sensors"
  | "telemetry_completeness_pct"
  | "average_pressure_bar"
  | "average_flow_m3h"
  | "detection_count"
  | "active_incident_count"
  | "average_asset_health"
  | "overdue_response_tasks"
>;

const COLUMNS: Array<{ key: SortKey; label: string }> = [
  { key: "zone", label: "Zone" },
  { key: "reporting_sensors", label: "Reporting sensors" },
  { key: "telemetry_completeness_pct", label: "Completeness" },
  { key: "average_pressure_bar", label: "Avg pressure" },
  { key: "average_flow_m3h", label: "Avg flow" },
  { key: "detection_count", label: "Detections" },
  { key: "active_incident_count", label: "Active incidents" },
  { key: "average_asset_health", label: "Avg asset health" },
  { key: "overdue_response_tasks", label: "Overdue tasks" },
];

function displayCell(row: ZoneAnalyticsRow, key: SortKey): string {
  if (!row.sufficient_data && (key === "average_pressure_bar" || key === "average_flow_m3h" || key === "telemetry_completeness_pct")) {
    return "Insufficient data";
  }
  const value = row[key];
  if (value === null) {
    return "Insufficient data";
  }
  if (typeof value === "number") {
    if (key === "telemetry_completeness_pct" || key === "average_asset_health") {
      return `${formatNumber(value, 1)}%`;
    }
    if (key === "average_pressure_bar") {
      return `${formatNumber(value, 2)} bar`;
    }
    if (key === "average_flow_m3h") {
      return `${formatNumber(value, 1)} m³/h`;
    }
    return formatNumber(value, 0);
  }
  return String(value);
}

interface ZoneTableProps {
  payload: AnalyticsZonesResponse;
}

export function ZoneTable({ payload }: ZoneTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("zone");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const rows = useMemo(() => {
    const copy = [...payload.items];
    copy.sort((left, right) => {
      const a = left[sortKey];
      const b = right[sortKey];
      if (a === null && b === null) return 0;
      if (a === null) return 1;
      if (b === null) return -1;
      if (typeof a === "number" && typeof b === "number") {
        return sortDir === "asc" ? a - b : b - a;
      }
      return sortDir === "asc"
        ? String(a).localeCompare(String(b))
        : String(b).localeCompare(String(a));
    });
    return copy;
  }, [payload.items, sortKey, sortDir]);

  const onSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((value) => (value === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDir(key === "zone" ? "asc" : "desc");
  };

  const exportCsv = () => {
    const csv = zoneRowsToCsv(rows, {
      range: payload.range,
      start: payload.start,
      end: payload.end,
      generatedAt: payload.generated_at,
      dataMode: payload.data_mode,
    });
    downloadTextFile(`aquapulse-zone-analytics-${payload.range}.csv`, csv);
  };

  return (
    <Card className="min-w-0 overflow-hidden p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-ink">Zone comparison</h3>
          <p className="mt-0.5 text-sm text-ink-muted">
            Simulated telemetry and recorded operational counts. Zones are not ranked with a
            single score.
          </p>
        </div>
        <Button variant="secondary" onClick={exportCsv}>
          Download CSV
        </Button>
      </div>
      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
              {COLUMNS.map((column) => (
                <th key={column.key} className="px-2 py-2 font-medium">
                  <button type="button" className="hover:text-ink" onClick={() => onSort(column.key)}>
                    {column.label}
                    {sortKey === column.key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.zone} className="border-b border-line/70 last:border-0">
                {COLUMNS.map((column) => (
                  <td key={column.key} className="px-2 py-2 text-ink">
                    {column.key === "zone" ? (
                      <Link
                        to={`/map?zone=${encodeURIComponent(row.zone)}`}
                        className="font-medium text-teal hover:underline"
                      >
                        {row.zone}
                      </Link>
                    ) : (
                      displayCell(row, column.key)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="grid grid-cols-1 gap-3 md:hidden">
        {rows.map((row) => (
          <li key={row.zone} className="rounded-2xl border border-line p-4">
            <Link to={`/map?zone=${encodeURIComponent(row.zone)}`} className="font-medium text-teal">
              {row.zone}
            </Link>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
              {COLUMNS.filter((column) => column.key !== "zone").map((column) => (
                <div key={column.key}>
                  <dt className="text-ink-muted">{column.label}</dt>
                  <dd className="text-ink">{displayCell(row, column.key)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </Card>
  );
}

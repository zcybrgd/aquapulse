import type { ReactNode } from "react";

import { ASSET_TYPE_LABELS, OPERATIONAL_STATUS_LABELS } from "../../lib/assets";
import { SEVERITY_LABELS, STATUS_LABELS } from "../../lib/incidents";
import type { MapFilters } from "../../types/map";
import { Button } from "../ui/Button";

interface MapFiltersBarProps {
  filters: MapFilters;
  zones: string[];
  compact?: boolean;
  hasActiveFilters: boolean;
  onChange: (patch: Partial<MapFilters>) => void;
  onClear: () => void;
}

function Field({
  id,
  label,
  value,
  onChange,
  children,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-ink-muted">
      {label}
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full rounded-xl border border-line bg-white px-2.5 text-sm font-normal normal-case text-ink"
      >
        {children}
      </select>
    </label>
  );
}

export function MapFiltersBar({
  filters,
  zones,
  compact = false,
  hasActiveFilters,
  onChange,
  onClear,
}: MapFiltersBarProps) {
  return (
    <div className={`min-w-0 ${compact ? "space-y-3" : "flex flex-wrap items-end gap-3"}`}>
      <div className={`grid min-w-0 gap-3 ${compact ? "grid-cols-1" : "grid-cols-2 xl:grid-cols-5"}`}>
        <Field id="map-zone" label="Zone" value={filters.zone} onChange={(value) => onChange({ zone: value })}>
          <option value="">All zones</option>
          {zones.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </Field>
        <Field
          id="map-asset-type"
          label="Asset type"
          value={filters.asset_type}
          onChange={(value) => onChange({ asset_type: value as MapFilters["asset_type"] })}
        >
          <option value="">All types</option>
          {Object.entries(ASSET_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Field>
        <Field
          id="map-asset-status"
          label="Asset status"
          value={filters.asset_status}
          onChange={(value) => onChange({ asset_status: value as MapFilters["asset_status"] })}
        >
          <option value="">All statuses</option>
          {Object.entries(OPERATIONAL_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Field>
        <Field
          id="map-severity"
          label="Incident severity"
          value={filters.incident_severity}
          onChange={(value) => onChange({ incident_severity: value as MapFilters["incident_severity"] })}
        >
          <option value="">All severities</option>
          {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Field>
        <Field
          id="map-incident-status"
          label="Incident status"
          value={filters.incident_status}
          onChange={(value) => onChange({ incident_status: value as MapFilters["incident_status"] })}
        >
          <option value="">Active default</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={filters.include_resolved}
          onChange={(event) => onChange({ include_resolved: event.target.checked })}
        />
        Show resolved
      </label>
      {hasActiveFilters ? (
        <Button variant="ghost" onClick={onClear} className="h-9 px-2.5">
          Clear filters
        </Button>
      ) : null}
    </div>
  );
}

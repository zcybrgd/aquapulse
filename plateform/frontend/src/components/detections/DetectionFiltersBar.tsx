import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";

import {
  PRIORITY_LABELS,
  RULE_LABELS,
  SORT_LABELS,
  STATUS_LABELS,
} from "../../lib/detections";
import type { DetectionFilters } from "../../types/detections";
import { Button } from "../ui/Button";

interface DetectionFiltersBarProps {
  filters: DetectionFilters;
  zones: string[];
  rules: string[];
  sensors: string[];
  resultCount: number;
  hasActiveFilters: boolean;
  onChange: (patch: Partial<DetectionFilters>) => void;
  onClear: () => void;
}

function SelectField({
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
    <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs font-medium text-ink-muted sm:min-w-[8.5rem]">
      {label}
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
      >
        {children}
      </select>
    </label>
  );
}

export function DetectionFiltersBar({
  filters,
  zones,
  rules,
  sensors,
  resultCount,
  hasActiveFilters,
  onChange,
  onClear,
}: DetectionFiltersBarProps) {
  const [searchValue, setSearchValue] = useState(filters.search);

  useEffect(() => {
    setSearchValue(filters.search);
  }, [filters.search]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (searchValue !== filters.search) {
        onChange({ search: searchValue });
      }
    }, 300);
    return () => window.clearTimeout(handle);
  }, [filters.search, onChange, searchValue]);

  return (
    <div className="card min-w-0 p-4 sm:p-5">
      <div className="flex flex-col gap-3">
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Search
          <span className="relative">
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
              aria-hidden="true"
            />
            <input
              type="search"
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder="Detection, sensor, rule or zone"
              className="h-10 w-full rounded-xl border border-line bg-white py-2 pl-9 pr-3 text-sm font-normal text-ink"
            />
          </span>
        </label>
        <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <SelectField
            id="det-status"
            label="Status"
            value={filters.status}
            onChange={(value) => onChange({ status: value as DetectionFilters["status"] })}
          >
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="det-priority"
            label="Screening priority"
            value={filters.priority}
            onChange={(value) => onChange({ priority: value as DetectionFilters["priority"] })}
          >
            <option value="">All priorities</option>
            {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
          <SelectField id="det-rule" label="Rule" value={filters.rule} onChange={(value) => onChange({ rule: value })}>
            <option value="">All rules</option>
            {rules.map((rule) => (
              <option key={rule} value={rule}>
                {RULE_LABELS[rule] ?? rule}
              </option>
            ))}
          </SelectField>
          <SelectField id="det-zone" label="Zone" value={filters.zone} onChange={(value) => onChange({ zone: value })}>
            <option value="">All zones</option>
            {zones.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="det-sensor"
            label="Sensor"
            value={filters.sensor}
            onChange={(value) => onChange({ sensor: value })}
          >
            <option value="">All sensors</option>
            {sensors.map((sensor) => (
              <option key={sensor} value={sensor}>
                {sensor}
              </option>
            ))}
          </SelectField>
          <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
            From
            <input
              type="datetime-local"
              value={filters.start}
              onChange={(event) => onChange({ start: event.target.value })}
              className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
            />
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
            To
            <input
              type="datetime-local"
              value={filters.end}
              onChange={(event) => onChange({ end: event.target.value })}
              className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
            />
          </label>
          <SelectField
            id="det-sort"
            label="Sort"
            value={`${filters.sort_by}:${filters.sort_order}`}
            onChange={(value) => {
              const [sort_by, sort_order] = value.split(":") as [
                DetectionFilters["sort_by"],
                DetectionFilters["sort_order"],
              ];
              onChange({ sort_by, sort_order });
            }}
          >
            {Object.entries(SORT_LABELS).map(([value, label]) => (
              <option key={`${value}-desc`} value={`${value}:desc`}>
                {label} · high to low
              </option>
            ))}
            <option value="detected_at:asc">Detected time · oldest</option>
          </SelectField>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-muted">
          Showing <span className="font-medium text-ink">{resultCount}</span> matching
          {resultCount === 1 ? " detection" : " detections"}
        </p>
        {hasActiveFilters ? (
          <Button variant="ghost" onClick={onClear} className="px-2.5">
            <X size={14} aria-hidden="true" />
            Clear filters
          </Button>
        ) : null}
      </div>
    </div>
  );
}

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";

import {
  CLASSIFICATION_LABELS,
  SEVERITY_LABELS,
  SORT_LABELS,
  STATUS_LABELS,
} from "../../lib/incidents";
import type { IncidentFilters } from "../../types/incidents";
import { Button } from "../ui/Button";

interface IncidentFiltersBarProps {
  filters: IncidentFilters;
  zones: string[];
  resultCount: number;
  hasActiveFilters: boolean;
  onChange: (patch: Partial<IncidentFilters>) => void;
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
    <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs font-medium text-ink-muted sm:min-w-[9.5rem]">
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

export function IncidentFiltersBar({
  filters,
  zones,
  resultCount,
  hasActiveFilters,
  onChange,
  onClear,
}: IncidentFiltersBarProps) {
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
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
        <label className="flex min-w-0 flex-[1.4] flex-col gap-1 text-xs font-medium text-ink-muted">
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
              placeholder="Incident, zone, asset or operator"
              className="h-10 w-full rounded-xl border border-line bg-white py-2 pl-9 pr-3 text-sm font-normal text-ink"
            />
          </span>
        </label>

        <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:flex-[3]">
          <SelectField
            id="severity-filter"
            label="Severity"
            value={filters.severity}
            onChange={(value) => onChange({ severity: value as IncidentFilters["severity"] })}
          >
            <option value="">All severities</option>
            {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="status-filter"
            label="Status"
            value={filters.status}
            onChange={(value) => onChange({ status: value as IncidentFilters["status"] })}
          >
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="classification-filter"
            label="Classification"
            value={filters.classification}
            onChange={(value) =>
              onChange({ classification: value as IncidentFilters["classification"] })
            }
          >
            <option value="">All classes</option>
            {Object.entries(CLASSIFICATION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="zone-filter"
            label="Zone"
            value={filters.zone}
            onChange={(value) => onChange({ zone: value })}
          >
            <option value="">All zones</option>
            {zones.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="sort-filter"
            label="Sort"
            value={`${filters.sort_by}:${filters.sort_order}`}
            onChange={(value) => {
              const [sort_by, sort_order] = value.split(":") as [
                IncidentFilters["sort_by"],
                IncidentFilters["sort_order"],
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
          {resultCount === 1 ? " incident" : " incidents"}
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

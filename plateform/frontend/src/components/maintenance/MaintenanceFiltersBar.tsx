import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Search, SlidersHorizontal, X } from "lucide-react";

import { ASSET_TYPE_LABELS } from "../../lib/assets";
import {
  ALL_MAINTENANCE_TYPES,
  ALL_PRIORITIES,
  ALL_STATUSES,
  MAINTENANCE_TYPE_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
} from "../../lib/maintenance";
import type { MaintenanceFilters } from "../../types/maintenance";
import { Button } from "../ui/Button";

interface MaintenanceFiltersBarProps {
  filters: MaintenanceFilters;
  zones: string[];
  resultCount: number;
  hasActiveFilters: boolean;
  onChange: (patch: Partial<MaintenanceFilters>) => void;
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
    <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
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

function FilterFields({
  filters,
  zones,
  onChange,
}: {
  filters: MaintenanceFilters;
  zones: string[];
  onChange: (patch: Partial<MaintenanceFilters>) => void;
}) {
  return (
    <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <SelectField id="maint-zone" label="Zone" value={filters.zone} onChange={(zone) => onChange({ zone })}>
        <option value="">All zones</option>
        {zones.map((zone) => (
          <option key={zone} value={zone}>
            {zone}
          </option>
        ))}
      </SelectField>
      <SelectField
        id="maint-asset-type"
        label="Asset type"
        value={filters.asset_type}
        onChange={(asset_type) => onChange({ asset_type: asset_type as MaintenanceFilters["asset_type"] })}
      >
        <option value="">All types</option>
        {Object.entries(ASSET_TYPE_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </SelectField>
      <SelectField
        id="maint-type"
        label="Maintenance type"
        value={filters.maintenance_type}
        onChange={(maintenance_type) =>
          onChange({ maintenance_type: maintenance_type as MaintenanceFilters["maintenance_type"] })
        }
      >
        <option value="">All types</option>
        {ALL_MAINTENANCE_TYPES.map((value) => (
          <option key={value} value={value}>
            {MAINTENANCE_TYPE_LABELS[value]}
          </option>
        ))}
      </SelectField>
      <SelectField
        id="maint-priority"
        label="Priority"
        value={filters.priority}
        onChange={(priority) => onChange({ priority: priority as MaintenanceFilters["priority"] })}
      >
        <option value="">All priorities</option>
        {ALL_PRIORITIES.map((value) => (
          <option key={value} value={value}>
            {PRIORITY_LABELS[value]}
          </option>
        ))}
      </SelectField>
      <SelectField
        id="maint-status"
        label="Status"
        value={filters.status}
        onChange={(status) => onChange({ status: status as MaintenanceFilters["status"] })}
      >
        <option value="">All statuses</option>
        {ALL_STATUSES.map((value) => (
          <option key={value} value={value}>
            {STATUS_LABELS[value]}
          </option>
        ))}
      </SelectField>
      <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
        Assignment
        <input
          id="maint-assigned"
          value={filters.assigned_to}
          onChange={(event) => onChange({ assigned_to: event.target.value })}
          className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
          placeholder="Technician name"
        />
      </label>
      <SelectField
        id="maint-sort"
        label="Sort"
        value={`${filters.sort_by}:${filters.sort_order}`}
        onChange={(value) => {
          const [sort_by, sort_order] = value.split(":") as [
            MaintenanceFilters["sort_by"],
            MaintenanceFilters["sort_order"],
          ];
          onChange({ sort_by, sort_order });
        }}
      >
        <option value="due_at:asc">Due date · soonest</option>
        <option value="due_at:desc">Due date · latest</option>
        <option value="priority:desc">Priority · highest</option>
        <option value="status:asc">Status</option>
        <option value="asset_name:asc">Asset name</option>
        <option value="created_at:desc">Created · newest</option>
      </SelectField>
      <label className="flex items-end gap-2 pb-2 text-sm font-medium text-ink">
        <input
          id="maint-overdue"
          type="checkbox"
          checked={filters.overdue}
          onChange={(event) => onChange({ overdue: event.target.checked })}
          className="h-4 w-4 rounded border-line"
        />
        Overdue only
      </label>
    </div>
  );
}

export function MaintenanceFiltersBar({
  filters,
  zones,
  resultCount,
  hasActiveFilters,
  onChange,
  onClear,
}: MaintenanceFiltersBarProps) {
  const [searchValue, setSearchValue] = useState(filters.search);
  const [drawerOpen, setDrawerOpen] = useState(false);

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
      <div className="flex flex-col gap-3 xl:flex-row xl:items-end">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs font-medium text-ink-muted">
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
              placeholder="Work order, asset, zone or assignee"
              className="h-10 w-full rounded-xl border border-line bg-white py-2 pl-9 pr-3 text-sm font-normal text-ink"
            />
          </span>
        </label>
        <Button
          variant="secondary"
          className="xl:hidden"
          onClick={() => setDrawerOpen((open) => !open)}
          aria-expanded={drawerOpen}
          aria-controls="maintenance-filter-drawer"
        >
          <SlidersHorizontal size={14} aria-hidden="true" />
          Filters
        </Button>
      </div>

      <div className="mt-4 hidden xl:block">
        <FilterFields filters={filters} zones={zones} onChange={onChange} />
      </div>

      {drawerOpen ? (
        <div id="maintenance-filter-drawer" className="mt-4 border-t border-line pt-4 xl:hidden">
          <FilterFields filters={filters} zones={zones} onChange={onChange} />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-muted">
          Showing <span className="font-medium text-ink">{resultCount}</span> matching
          {resultCount === 1 ? " work order" : " work orders"}
          {filters.asset_id ? ` for ${filters.asset_id}` : ""}
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

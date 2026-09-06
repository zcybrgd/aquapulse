import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";

import {
  ASSET_SORT_LABELS,
  ASSET_TYPE_LABELS,
  DEFAULT_ASSET_SORT_BY,
  DEFAULT_ASSET_SORT_ORDER,
  OPERATIONAL_STATUS_LABELS,
} from "../../lib/assets";
import type { AssetFilters } from "../../types/assets";
import { Button } from "../ui/Button";

interface AssetFiltersBarProps {
  filters: AssetFilters;
  zones: string[];
  resultCount: number;
  hasActiveFilters: boolean;
  onChange: (patch: Partial<AssetFilters>) => void;
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

export function AssetFiltersBar({
  filters,
  zones,
  resultCount,
  hasActiveFilters,
  onChange,
  onClear,
}: AssetFiltersBarProps) {
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
              placeholder="ID, name, manufacturer, model or serial"
              className="h-10 w-full rounded-xl border border-line bg-white py-2 pl-9 pr-3 text-sm font-normal text-ink"
            />
          </span>
        </label>
        <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:flex-[3]">
          <SelectField
            id="asset-type-filter"
            label="Asset type"
            value={filters.asset_type}
            onChange={(value) => onChange({ asset_type: value as AssetFilters["asset_type"] })}
          >
            <option value="">All types</option>
            {Object.entries(ASSET_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="asset-status-filter"
            label="Status"
            value={filters.status}
            onChange={(value) => onChange({ status: value as AssetFilters["status"] })}
          >
            <option value="">All statuses</option>
            {Object.entries(OPERATIONAL_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="asset-zone-filter"
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
            id="asset-maintenance-filter"
            label="Maintenance"
            value={filters.maintenance}
            onChange={(value) => onChange({ maintenance: value as AssetFilters["maintenance"] })}
          >
            <option value="">All maintenance</option>
            <option value="due">Due now</option>
            <option value="upcoming">Due within 30 days</option>
            <option value="scheduled">Scheduled</option>
          </SelectField>
          <SelectField
            id="asset-sort-filter"
            label="Sort"
            value={`${filters.sort_by}:${filters.sort_order}`}
            onChange={(value) => {
              const [sort_by, sort_order] = value.split(":") as [
                AssetFilters["sort_by"],
                AssetFilters["sort_order"],
              ];
              onChange({ sort_by, sort_order });
            }}
          >
            <option value={`${DEFAULT_ASSET_SORT_BY}:${DEFAULT_ASSET_SORT_ORDER}`}>
              Health · worst first
            </option>
            {Object.entries(ASSET_SORT_LABELS).map(([value, label]) => (
              <option key={`${value}-desc`} value={`${value}:desc`}>
                {label} · high to low
              </option>
            ))}
            <option value="name:asc">Name · A to Z</option>
            <option value="last_seen:asc">Last seen · oldest</option>
          </SelectField>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-muted">
          Showing <span className="font-medium text-ink">{resultCount}</span> matching
          {resultCount === 1 ? " asset" : " assets"}
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

import { AssetFiltersBar } from "../components/assets/AssetFiltersBar";
import { AssetCardList, AssetTable } from "../components/assets/AssetList";
import { AssetRegistryHeader } from "../components/assets/AssetRegistryHeader";
import { AssetListSkeleton } from "../components/assets/AssetSkeletons";
import { AssetSummaryCards } from "../components/assets/AssetSummaryCards";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { useAssetFilters } from "../hooks/useAssetFilters";
import { useAssets } from "../hooks/useAssets";
import { formatDateTime } from "../lib/format";

export function AssetsPage() {
  const { filters, setFilters, clearFilters, hasActiveFilters } = useAssetFilters();
  const { items, total, summary, zones, lastSeen, loading, error, reload } = useAssets(filters);

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      <AssetRegistryHeader
        summary={summary}
        lastSeen={lastSeen ? formatDateTime(lastSeen) : null}
        ready={!loading && !error}
      />

      {loading ? <AssetListSkeleton /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}

      {!loading && !error ? (
        <>
          <AssetSummaryCards summary={summary} />
          <AssetFiltersBar
            filters={filters}
            zones={zones}
            resultCount={total}
            hasActiveFilters={hasActiveFilters}
            onChange={setFilters}
            onClear={clearFilters}
          />
          {items.length === 0 ? (
            <div className="card">
              <EmptyState
                title="No assets match these filters"
                description="Clear filters or try a different zone, type or search term."
              />
            </div>
          ) : (
            <>
              <AssetTable items={items} />
              <AssetCardList items={items} />
            </>
          )}
        </>
      ) : null}
    </div>
  );
}

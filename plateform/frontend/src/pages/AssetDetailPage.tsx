import { Link, useLocation, useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

import { AssetDetailHeader } from "../components/assets/AssetDetailHeader";
import { AssetHealthChart } from "../components/assets/AssetHealthChart";
import { AssetLocationPanel } from "../components/assets/AssetLocationPanel";
import { AssetMaintenancePanel } from "../components/assets/AssetMaintenancePanel";
import { AssetOverviewPanel } from "../components/assets/AssetOverviewPanel";
import { AssetRelatedIncidents } from "../components/assets/AssetRelatedIncidents";
import { AssetDetailSkeleton } from "../components/assets/AssetSkeletons";
import { AssetTypePanel } from "../components/assets/AssetTypePanel";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { useAssetDetail } from "../hooks/useAssetDetail";

export function AssetDetailPage() {
  const { assetId } = useParams();
  const location = useLocation();
  const { asset, health, range, setRange, loading, refreshing, notFound, error, backgroundError, lastRefreshAt, reload } = useAssetDetail(assetId);
  const reduceMotion = useReducedMotion();

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      {loading ? <AssetDetailSkeleton /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && notFound ? (
        <div className="card p-6">
          <Link
            to={`/assets${location.search}`}
            className="text-sm font-medium text-teal hover:underline"
          >
            Back to Asset Registry
          </Link>
          <EmptyState
            title="Asset not found"
            description="This asset ID is not in the current registry. Return to the Asset Registry and choose another record."
          />
        </div>
      ) : null}

      {!loading && asset ? (
        <motion.div
          className="flex flex-col gap-6"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut" }}
        >
          <AssetDetailHeader asset={asset} />
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(20rem,1fr)]">
            <div className="flex min-w-0 flex-col gap-4">
              <AssetOverviewPanel asset={asset} />
              <AssetTypePanel asset={asset} />
              {health ? (
                <AssetHealthChart
                  assetType={asset.asset_type}
                  health={health}
                  range={range}
                  onRangeChange={setRange}
                  refreshing={refreshing}
                  lastRefreshAt={lastRefreshAt}
                  backgroundError={backgroundError}
                  onRefresh={reload}
                />
              ) : null}
            </div>
            <div className="flex min-w-0 flex-col gap-4">
              <AssetLocationPanel asset={asset} />
              <AssetMaintenancePanel asset={asset} />
              <AssetRelatedIncidents incidents={asset.related_incidents} />
            </div>
          </div>
        </motion.div>
      ) : null}
    </div>
  );
}

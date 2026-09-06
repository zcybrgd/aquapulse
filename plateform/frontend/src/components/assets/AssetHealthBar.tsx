import { formatNumber } from "../../lib/format";
import { healthBand, healthBandLabel } from "../../lib/assets";

interface AssetHealthBarProps {
  score: number | null;
}

export function AssetHealthBar({ score }: AssetHealthBarProps) {
  const band = healthBand(score);
  const width = score === null ? 0 : Math.max(0, Math.min(100, score));
  const tone =
    band === "healthy" ? "bg-teal" : band === "fair" ? "bg-warning" : band === "poor" ? "bg-critical" : "bg-line";

  return (
    <div className="min-w-0">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-ink">
          {score === null ? "—" : formatNumber(score, 0)}
        </p>
        <p className="text-xs text-ink-muted">{healthBandLabel(score)}</p>
      </div>
      <div
        className="mt-1 h-1.5 overflow-hidden rounded-full bg-line"
        role="meter"
        aria-label={`Health score ${score === null ? "unknown" : `${formatNumber(score, 0)}, ${healthBandLabel(score)}`}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score === null ? undefined : Math.round(score)}
        title="Health score is a 0–100 composite of connectivity, battery and recent device integrity."
      >
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

import { Link } from "react-router-dom";

import { statusLabel, type MappingRow } from "../../lib/agentAuditDisplay";
import { Card } from "../ui/Card";
import { AuditStatusBadge } from "./AuditStatusBadge";

export function IdentityMappingSection({
  rows,
  warnings,
}: {
  rows: MappingRow[];
  warnings: string[];
}) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Identity mapping</h3>
      <p className="mt-1 text-sm text-ink-muted">
        AquaPulse never guesses a mapping from an external identifier.
      </p>
      {rows.length === 0 ? (
        <p className="mt-4 text-sm text-ink-muted">No external identities were supplied for this run.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {rows.map((row) => (
            <li key={`${row.entityType}-${row.externalId}`} className="min-w-0 rounded-xl bg-page px-3 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium text-ink">{row.label}</p>
                <AuditStatusBadge value={row.mapped ? "mapped" : "unmapped"} label={statusLabel(row.mapped ? "mapped" : "unmapped")} />
              </div>
              <p className="mt-1 break-words text-sm text-ink">{row.externalId}</p>
              {row.mapped && row.mappedId ? (
                row.href ? (
                  <Link to={row.href} className="mt-1 inline-block text-sm font-medium text-teal hover:underline">
                    {row.mappedId}
                  </Link>
                ) : (
                  <p className="mt-1 text-sm text-ink">{row.mappedId}</p>
                )
              ) : (
                <p className="mt-2 text-sm text-warning">External identity is not mapped to an AquaPulse entity.</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {warnings.length > 0 ? (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-ink">Mapping warnings</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </Card>
  );
}

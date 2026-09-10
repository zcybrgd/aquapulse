import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { auditEvent, auditRun, findingRecord, integrationRun, recommendationRecord } from "../../test/agentAuditFixtures";
import {
  mappingRows,
  mappingWarningMessages,
  mergeInvestigationFindings,
  mergeResponseResult,
  rawPayload,
  readInvestigationBatch,
  validationLabel,
} from "../../lib/agentAuditDisplay";
import { AuditRunTimeline } from "./AuditRunTimeline";
import { IdentityMappingSection } from "./IdentityMappingSection";
import { InvestigationResultSection } from "./InvestigationFindingCard";
import { RawPayloadSection } from "./RawPayloadSection";
import { ResponseAgentResult } from "./ResponseAgentResult";

function renderView(node: ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("investigation findings", () => {
  it("renders several finding cards from stored investigation results", () => {
    const findings = mergeInvestigationFindings(auditRun(), [
      findingRecord({ id: "f1", external_cluster_id: "cluster-desert-042" }),
      findingRecord({
        id: "f2",
        external_anomaly_id: "036305c7-7187-4b00-a641-01a1221e87fa",
        classification: "confirmed_instrument_fault",
        external_cluster_id: "cluster-desert-043",
        confidence_score: 0.6643,
        severity_tier: 1,
      }),
      findingRecord({
        id: "f3",
        external_anomaly_id: "b2222222-2222-4222-8222-222222222222",
        classification: "confirmed_instrument_fault",
        external_cluster_id: "cluster-desert-044",
        confidence_score: 0.7011,
        severity_tier: 1,
      }),
    ], null);
    const batch = readInvestigationBatch(integrationRun().response_payload);
    renderView(
      <InvestigationResultSection
        batchId={batch.batchId}
        analysisTimestamp={batch.analysisTimestamp}
        totalClustersAnalyzed={batch.totalClustersAnalyzed}
        anomaliesDetected={batch.anomaliesDetected}
        validation="Validated"
        findings={findings}
      />,
    );
    expect(screen.getByText("Agent-assessed anomaly")).toBeInTheDocument();
    expect(screen.getAllByText("Agent-assessed instrument fault")).toHaveLength(2);
    expect(screen.getAllByText("Agent assessment — not independently confirmed")).toHaveLength(3);
    expect(screen.getByText("cluster-desert-044")).toBeInTheDocument();
  });

  it("shows Unavailable for null optional finding fields and omits estimated volume loss", () => {
    const [finding] = mergeInvestigationFindings(auditRun(), [
      findingRecord({
        physical_deviations: {
          pressure_drop_pct: null,
          flow_surge_pct: null,
          pressure_slope: null,
          flow_slope: null,
          is_stale_pre_outage_data: null,
        },
        criticality_metrics: {
          criticality_score: 1,
          proximity_to_reservoir_m: null,
          population_served: null,
          associated_valve_id: null,
          pipe_diameter_mm: null,
        },
        network_status: {
          camara_reachability_status: "UNKNOWN",
          camara_congestion_level: "HIGH",
          api_unavailable: true,
        },
        operator_justification: null,
      }),
    ], null);
    renderView(
      <InvestigationResultSection
        batchId="batch-demo"
        analysisTimestamp={null}
        totalClustersAnalyzed={null}
        anomaliesDetected={null}
        validation="Validated"
        findings={[finding]}
      />,
    );
    expect(screen.queryByText("Estimated volume loss")).not.toBeInTheDocument();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Network context reported by the Investigation Agent").length).toBeGreaterThan(0);
  });
});

describe("identity mapping", () => {
  it("warns on unmapped external IDs and does not invent links", () => {
    const findings = mergeInvestigationFindings(auditRun(), [findingRecord()], null);
    const rows = mappingRows(findings, null, []);
    const warnings = mappingWarningMessages([
      {
        entity_type: "sensor_cluster",
        external_id: "cluster-desert-042",
        message: "No configured mapping exists for this external identity.",
      },
    ]);
    renderView(<IdentityMappingSection rows={rows} warnings={warnings} />);
    expect(screen.getAllByText("External identity is not mapped to an AquaPulse entity.").length).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: /DET-|INC-|VLV-/ })).not.toBeInTheDocument();
    expect(screen.getAllByText(/cluster-desert-042/).length).toBeGreaterThan(0);
    expect(screen.getByText(/No configured mapping exists/)).toBeInTheDocument();
  });
});

describe("response agent result", () => {
  it("renders a readable recommendation", () => {
    const result = mergeResponseResult(
      auditRun({ agent_type: "response_agent", recommendation_decisions: ["ALERT_AND_AWAIT"] }),
      [recommendationRecord()],
      { operator_message: "Alert the control room" },
    );
    renderView(<ResponseAgentResult result={result!} />);
    expect(screen.getAllByText("Alert and await approval").length).toBeGreaterThan(0);
    expect(screen.getByText("Alert the control room")).toBeInTheDocument();
    expect(screen.getByText("reachability_check")).toBeInTheDocument();
    expect(screen.getByText("Agent-provided reasoning — not independently verified")).toBeInTheDocument();
  });

  it("does not present a blocked isolation request as executed", () => {
    const result = mergeResponseResult(
      auditRun({
        agent_type: "response_agent",
        decision: "AUTONOMOUS_ISOLATE",
        recommendation_decisions: ["AUTONOMOUS_ISOLATE"],
      }),
      [
        recommendationRecord({
          decision: "AUTONOMOUS_ISOLATE",
          safety_status: "blocked",
          valve_command_sent: false,
          valve_command_confirmed: false,
          valve_command_verified: false,
        }),
      ],
      null,
    );
    renderView(<ResponseAgentResult result={result!} />);
    expect(screen.getAllByText("Isolation requested").length).toBeGreaterThan(0);
    expect(screen.getByText("Not executed")).toBeInTheDocument();
    expect(screen.getByText("Blocked by AquaPulse safety policy")).toBeInTheDocument();
    expect(screen.queryByText("Independently verified")).not.toBeInTheDocument();
  });
});

describe("audit timeline", () => {
  it("shows the empty timeline copy when no events exist", () => {
    renderView(<AuditRunTimeline run={auditRun({ events: [] })} />);
    expect(screen.getByText("No audit events recorded")).toBeInTheDocument();
    expect(screen.getByText("Events will appear here after a real agent run.")).toBeInTheDocument();
  });

  it("labels a running run with stored events as a partial timeline", () => {
    renderView(
      <AuditRunTimeline
        run={auditRun({
          status: "running",
          events: [
            auditEvent({ occurred_at: "2026-09-09T22:49:10.000Z", summary: "Validation started" }),
            auditEvent({
              id: "evt-2",
              sequence_number: 2,
              occurred_at: "2026-09-09T22:49:12.000Z",
              summary: "Finding accepted",
            }),
          ],
        })}
      />,
    );
    expect(screen.getByText("Partial audit timeline")).toBeInTheDocument();
    expect(screen.getByText("Validation started")).toBeInTheDocument();
  });
});

describe("raw payload", () => {
  it("is collapsed by default and copies pretty-printed JSON", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    const payload = rawPayload(integrationRun());
    renderView(<RawPayloadSection payload={payload} />);
    const details = screen.getByTestId("raw-payload");
    expect(details).not.toHaveAttribute("open");
    expect(screen.getByText("Technical details — raw sanitized payload")).toBeInTheDocument();
    await user.click(screen.getByText("Copy JSON"));
    expect(writeText).toHaveBeenCalledWith(JSON.stringify(payload, null, 2));
  });
});

describe("mobile layout", () => {
  it("stacks investigation findings in expandable cards", () => {
    const findings = mergeInvestigationFindings(auditRun(), [findingRecord(), findingRecord({ id: "f2" })], null);
    const { container } = renderView(
      <div className="w-[390px] overflow-x-hidden">
        <InvestigationResultSection
          batchId="batch-demo"
          analysisTimestamp={null}
          totalClustersAnalyzed={3}
          anomaliesDetected={2}
          validation={validationLabel(auditRun(), integrationRun())}
          findings={findings}
        />
      </div>,
    );
    expect(container.querySelectorAll("details").length).toBe(2);
    expect(container.querySelector(".grid-cols-1")).not.toBeNull();
    expect(within(container).getAllByText("Show details").length).toBe(2);
  });
});

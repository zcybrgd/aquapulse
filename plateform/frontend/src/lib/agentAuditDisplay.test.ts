import { describe, expect, it } from "vitest";

import { auditEvent, auditRun, findingRecord, recommendationRecord } from "../test/agentAuditFixtures";
import {
  auditTimelineHeading,
  mappingRows,
  mappingWarningMessages,
  mergeInvestigationFindings,
  mergeResponseResult,
  readEstimatedVolumeLoss,
  readInvestigationBatch,
  readReasoningSteps,
  sanitizeDisplayValue,
} from "./agentAuditDisplay";

describe("agent audit display parsers", () => {
  it("reads investigation batch fields from the stored payload", () => {
    const batch = readInvestigationBatch({
      batch: {
        batch_id: "batch-demo",
        analysis_timestamp: "2026-08-31T02:00:00Z",
        total_clusters_analyzed: 3,
        anomalies_detected_count: 3,
      },
    });
    expect(batch.batchId).toBe("batch-demo");
    expect(batch.totalClustersAnalyzed).toBe(3);
  });

  it("keeps null optional physical fields instead of coercing them to zero", () => {
    const [finding] = mergeInvestigationFindings(auditRun(), [
      findingRecord({
        physical_deviations: {
          pressure_drop_pct: null,
          flow_surge_pct: 12.5,
        },
        criticality_metrics: {
          proximity_to_reservoir_m: null,
          population_served: null,
          pipe_diameter_mm: null,
        },
      }),
    ], null);
    expect(finding.physical.pressure_drop_pct).toBeNull();
    expect(readEstimatedVolumeLoss(finding.physical)).toBeNull();
    expect(finding.criticality.population_served).toBeNull();
  });

  it("does not invent a mapped AquaPulse entity for an unmapped external ID", () => {
    const rows = mappingRows(
      mergeInvestigationFindings(auditRun(), [findingRecord()], null),
      null,
      [],
    );
    const cluster = rows.find((row) => row.entityType === "sensor_cluster");
    expect(cluster?.mapped).toBe(false);
    expect(cluster?.href).toBeNull();
  });

  it("maps a response recommendation without treating isolation as executed", () => {
    const result = mergeResponseResult(
      auditRun({
        agent_code: "response_agent",
        agent_type: "response_agent",
        decision: "AUTONOMOUS_ISOLATE",
        recommendation_decisions: ["AUTONOMOUS_ISOLATE"],
        valve_command_sent: false,
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
      { decision: "AUTONOMOUS_ISOLATE", operator_message: "Isolate the northern valve" },
    );
    expect(result?.decision).toBe("AUTONOMOUS_ISOLATE");
    expect(result?.valveCommandSent).toBe(false);
    expect(result?.valveCommandVerified).toBe(false);
    expect(result?.operatorMessage).toBe("Isolate the northern valve");
    expect(result?.blockedReason).toBe("Blocked by AquaPulse safety policy");
  });

  it("sorts timeline titles from real event presence and run status", () => {
    expect(auditTimelineHeading({ status: "succeeded", events: [] })).toBe("No audit events recorded");
    expect(auditTimelineHeading({ status: "running", events: [auditEvent()] })).toBe("Partial audit timeline");
    expect(auditTimelineHeading({ status: "succeeded", events: [auditEvent()] })).toBe("Chronological stage timeline");
  });

  it("reads reasoning as chronological steps and redacts secrets", () => {
    expect(readReasoningSteps([{ step: "reachability_check" }, { step: "planner" }])).toEqual([
      "reachability_check",
      "planner",
    ]);
    const sanitized = sanitizeDisplayValue({
      api_key: "secret",
      operator_contact: { phone: "+9715" },
      safe: "ok",
      path: "C:\\Users\\Admin\\secrets.env",
    });
    expect(sanitized).toMatchObject({
      api_key: "[REDACTED]",
      operator_contact: "[REDACTED]",
      safe: "ok",
      path: "[REDACTED]",
    });
  });

  it("lists mapping warnings instead of only a count", () => {
    const messages = mappingWarningMessages([
      {
        entity_type: "sensor_cluster",
        external_id: "cluster-desert-042",
        message: "No configured mapping exists for this external identity.",
      },
    ]);
    expect(messages[0]).toContain("cluster-desert-042");
    expect(messages[0]).toContain("No configured mapping");
  });
});

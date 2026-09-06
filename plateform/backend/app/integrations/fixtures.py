"""Deterministic contract fixtures. No secrets or real operator contacts."""

from copy import deepcopy

INVESTIGATION_EXAMPLE_BATCH = {
    "batch_id": "batch-2026-08-31-001",
    "analysis_timestamp": "2026-08-31T02:00:00Z",
    "total_clusters_analyzed": 3,
    "anomalies_detected_count": 3,
    "investigated_threats": [
        {
            "anomaly_id": "e048d424-6a15-47ed-a35c-b3cc4c5ff445",
            "sensor_cluster_id": "cluster-desert-042",
            "segment_id": "seg-neom-north-01",
            "classification": "confirmed_anomaly",
            "severity_tier": 3,
            "network_status": {
                "camara_reachability_status": "REACHABLE",
                "camara_congestion_level": "LOW",
                "api_unavailable": False,
            },
            "physical_deviations": {
                "pressure_drop_pct": 36.6071,
                "flow_surge_pct": 40.2743,
                "pressure_slope": -1.9033,
                "flow_slope": 3.9317,
                "is_stale_pre_outage_data": False,
            },
            "criticality_metrics": {
                "criticality_score": 3,
                "proximity_to_reservoir_m": 120.0,
                "population_served": 45000,
                "associated_valve_id": "valve-neom-north-01",
                "pipe_diameter_mm": 400.0,
            },
            "operator_justification": "Operator justification text",
            "confidence_score": 0.9078,
        },
        {
            "anomaly_id": "036305c7-7187-4b00-a641-01a1221e87fa",
            "sensor_cluster_id": "cluster-desert-043",
            "segment_id": "seg-neom-north-02",
            "classification": "confirmed_instrument_fault",
            "severity_tier": 1,
            "network_status": {
                "camara_reachability_status": "UNREACHABLE",
                "camara_congestion_level": "LOW",
                "api_unavailable": False,
            },
            "physical_deviations": {
                "pressure_drop_pct": 0.22172949002217607,
                "flow_surge_pct": 0.13333333333332575,
                "pressure_slope": -0.030000000000001633,
                "flow_slope": 0.02999999999999368,
                "is_stale_pre_outage_data": True,
            },
            "criticality_metrics": {
                "criticality_score": 2,
                "proximity_to_reservoir_m": 2400.0,
                "population_served": 8000,
                "associated_valve_id": "valve-neom-north-02",
                "pipe_diameter_mm": 250.0,
            },
            "operator_justification": "Operator justification text",
            "confidence_score": 0.6643,
        },
        {
            "anomaly_id": "b2222222-2222-4222-8222-222222222222",
            "sensor_cluster_id": "cluster-desert-044",
            "segment_id": "seg-neom-north-03",
            "classification": "confirmed_instrument_fault",
            "severity_tier": 1,
            "network_status": {
                "camara_reachability_status": "UNKNOWN",
                "camara_congestion_level": "HIGH",
                "api_unavailable": True,
            },
            "physical_deviations": {
                "pressure_drop_pct": 2.0,
                "flow_surge_pct": 1.1,
                "pressure_slope": 0.0,
                "flow_slope": 0.0,
                "is_stale_pre_outage_data": True,
            },
            "criticality_metrics": {
                "criticality_score": 1,
                "proximity_to_reservoir_m": None,
                "population_served": None,
                "associated_valve_id": None,
                "pipe_diameter_mm": None,
            },
            "operator_justification": "Pattern matches a stale instrument rather than a leak.",
            "confidence_score": 0.7011,
        },
    ],
}


def investigation_example_batch() -> dict:
    return deepcopy(INVESTIGATION_EXAMPLE_BATCH)


def response_result_fixture(decision: str, *, result_id: str = "res-demo-001") -> dict:
    confirmed = decision == "AUTONOMOUS_ISOLATE"
    return {
        "schema_version": "1.0",
        "result_id": result_id,
        "incident_id": "INC-1835",
        "cluster_id": "cluster-desert-042",
        "device_id": "valve-neom-north-01",
        "severity_tier": 3 if decision == "AUTONOMOUS_ISOLATE" else 2 if decision == "ALERT_AND_AWAIT" else 1,
        "reachability": {"status": "UNREACHABLE" if decision == "ESCALATE_UNREACHABLE" else "REACHABLE"},
        "decision": decision,
        "notification_sent": False,
        "valve_command_sent": confirmed,
        "valve_command_confirmed": confirmed,
        "human_override_requested": decision in {"ALERT_AND_AWAIT", "AUTONOMOUS_ISOLATE"},
        "human_override_response": None,
        "reasoning_trace": [{"step": "reachability_check"}, {"step": "llm_response_planner"}],
        "created_at": "2026-09-01T07:45:00Z",
        "audit": {
            "entry_id": f"audit-{result_id}",
            "incident_id": "INC-1835",
            "cluster_id": "cluster-desert-042",
            "severity_tier": 3 if decision == "AUTONOMOUS_ISOLATE" else 2,
            "network_grant": {"granted": False},
            "network_denied": {"denied": True, "reason": "camara_disabled"},
            "actuation_result": "not_executed",
            "logged_at": "2026-09-01T07:45:00Z",
        },
    }


INVESTIGATION_EXAMPLE_REQUEST = {
    "schema_version": "1.0",
    "run_id": "AGRUN-000001",
    "requested_at": "2026-09-01T07:45:00Z",
    "data_mode": "simulated",
    "batch": {
        "batch_id": "AP-BATCH-000001",
        "analysis_timestamp": "2026-09-01T07:45:00Z",
        "clusters": [
            {
                "cluster_id": "AP-CLUSTER-DET-000001",
                "external_aliases": [],
                "segment_id": "HBR-XFER-7",
                "sensor_ids": ["SNS-HBR-007"],
                "telemetry_window": {
                    "start": "2026-09-01T06:45:00Z",
                    "end": "2026-09-01T07:45:00Z",
                },
                "pressure": {"value": None, "values": None, "unit": "kPa", "available": False},
                "flow": {"value": None, "values": None, "unit": "L/s", "available": False},
                "data_freshness": "fresh",
                "network_context": {"zone": "Dubai Harbour"},
                "temperature": {"value": None, "values": None, "unit": "°C", "available": False},
                "criticality": 3,
                "population_served": None,
                "associated_valve_id": None,
                "pipe_diameter_mm": None,
                "pipe_diameter_available": False,
                "population_available": False,
                "data_mode": "simulated",
            }
        ],
    },
}

RESPONSE_EXAMPLE_REQUEST = {
    "schema_version": "1.0",
    "run_id": "AGRUN-000002",
    "requested_at": "2026-09-01T07:45:00Z",
    "data_mode": "simulated",
    "incident_id": "INC-1835",
    "cluster_id": "AP-CLUSTER-DET-000001",
    "device_id": "VLV-HBR-007",
    "severity_tier": 2,
    "network_grant": {"granted": False, "data_mode": "mock"},
    "network_denied": {"denied": True, "reason": "camara_disabled", "data_mode": "mock"},
    "operator_contact": {"display_name": "Demo Operator", "channel": "unconfigured"},
}

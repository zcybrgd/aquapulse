CONTRACT_VERSION = "1.0"
INVESTIGATION_AGENT = "investigation_agent"
RESPONSE_AGENT = "response_agent"

CLASSIFICATION_ANOMALY = "confirmed_anomaly"
CLASSIFICATION_FAULT = "confirmed_instrument_fault"
CLASSIFICATION_LABELS = {
    CLASSIFICATION_ANOMALY: "Agent-assessed anomaly",
    CLASSIFICATION_FAULT: "Agent-assessed instrument fault",
}

DECISIONS = ("LOG_ONLY", "ALERT_AND_AWAIT", "AUTONOMOUS_ISOLATE", "ESCALATE_UNREACHABLE")
SEVERITY_TIERS = (1, 2, 3)
SEVERITY_LABELS = {
    1: "Tier 1 / monitor",
    2: "Tier 2 / alert and human review",
    3: "Tier 3 / critical recommendation requiring platform safety policy",
}

ENTITY_TYPES = ("sensor_cluster", "sensor", "segment", "valve", "device", "incident", "detection")

SAFETY_ADVISORY = "advisory"
SAFETY_BLOCKED = "blocked"
SAFETY_UNVERIFIED = "agent_reported_unverified"

EXECUTION_DISABLED_MESSAGE = "Agent execution is disabled"
PHYSICAL_BLOCKED_REASON = "physical_commands_disabled"
NOTIFICATIONS_DISABLED_REASON = "notifications_disabled"
CAMARA_DISABLED_REASON = "camara_disabled"

MOCK_DATA_MODE = "mock_agent_data"
NETWORK_AGENT_CODE = "network_management_agent"
NETWORK_CONTRACT = "draft-unconfirmed"
NETWORK_EVENT_TYPES = (
    "connectivity_check",
    "qod_requested",
    "qod_granted",
    "qod_denied",
    "qod_released",
    "agent_error",
)
PIPELINE_STAGES = (
    "lightweight_detection",
    "anomaly_investigation",
    "network_management",
    "response",
    "platform_safety",
    "audit",
)
RESPONSE_NODES = (
    "reachability_check",
    "llm_response_planner",
    "execute_response",
    "human_override",
    "audit_writer",
)

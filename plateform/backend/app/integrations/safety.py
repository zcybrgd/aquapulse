"""AquaPulse owns authorization. Agent output is never treated as approval."""

from app.integrations.constants import SAFETY_ADVISORY, SAFETY_BLOCKED, SAFETY_UNVERIFIED
from app.integrations.contracts.response import ResponseResultV1


def evaluate_response_safety(result: ResponseResultV1) -> dict:
    """Enforce recommendation → validation → human approval → safe execution.

    Step 11 never executes or confirms a physical command, including AUTONOMOUS_ISOLATE.
    CAMARA grants, severity, confidence, and reasoning traces are not authorization.
    """
    reported_valve = bool(result.valve_command_sent or result.valve_command_confirmed)
    if result.decision == "AUTONOMOUS_ISOLATE" or reported_valve:
        safety_status = SAFETY_UNVERIFIED if reported_valve else SAFETY_BLOCKED
        return {
            "safety_status": safety_status,
            "authorized": False,
            "execution_allowed": False,
            "human_approval_inferred": False,
            "valve_command_verified": False,
            "notification_verified": False,
            "reason": "physical_commands_disabled",
            "policy": (
                "Agent recommendation is advisory. AquaPulse validation rejected actuation. "
                "Human approval is required before any future safe execution gateway."
            ),
        }
    return {
        "safety_status": SAFETY_ADVISORY,
        "authorized": False,
        "execution_allowed": False,
        "human_approval_inferred": False,
        "valve_command_verified": False,
        "notification_verified": False,
        "reason": "advisory_only",
        "policy": "Response Agent results are recommendations. AquaPulse remains the authority.",
    }


def never_infer_human_approval(result: ResponseResultV1) -> bool:
    _ = result.human_override_requested
    _ = result.human_override_response
    _ = result.decision
    _ = result.severity_tier
    return False

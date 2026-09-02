from __future__ import annotations
import logging
from ..schemas import ActuationDecision, SeverityTier
from ..state import ActuationState
from ..tools.actuator_client import ValveActuatorClient, ValveCommandError
from ..tools.notification_client import NotificationClient
logger = logging.getLogger("actuation_agent.nodes.execute_response")

def make_execute_response_node(notification_client: NotificationClient,actuator_client: ValveActuatorClient,):
    def execute_response_node(state: ActuationState) -> ActuationState:
        tier: SeverityTier = state["severity_tier"]
        reachability = state["reachability"]
        incident_id = state["incident_id"]
        device_id = state["device_id"]
        operator_contact = state.get("operator_contact", "")
        trace = list(state.get("reasoning_trace", []))
        notification_sent = False
        valve_command_sent = False
        valve_command_confirmed = False
        human_override_requested = False
        if not reachability.reachable:
            decision = ActuationDecision.ESCALATE_UNREACHABLE
            message = (f"URGENT: Incident {incident_id} on device {device_id} could not be "
            f"confirmed reachable. Tier {int(tier)} response requires manual "
            f"intervention — automated actuation withheld for safety.")
            notification_sent = notification_client.send(recipient=operator_contact, message=message,channel="sms", incident_id=incident_id,)
            trace.append("Escalated to human operator: device unreachable, no autonomous action taken.")
        elif tier == SeverityTier.TIER_1_MONITOR:
            decision = ActuationDecision.LOG_ONLY
            trace.append("Tier 1: logged for monitoring, no operator interruption, no network/valve action.")
        elif tier == SeverityTier.TIER_2_ALERT:
            decision = ActuationDecision.ALERT_AND_AWAIT
            message = (f"Incident {incident_id} on device {device_id}: Tier 2 anomaly confirmed. "
                f"Guaranteed connectivity is active. Please review and confirm recommended action.")
            notification_sent = notification_client.send(recipient=operator_contact, message=message,channel="sms", incident_id=incident_id,)
            trace.append("Tier 2: operator alerted with full context, awaiting confirmation before any physical action.")

        elif tier == SeverityTier.TIER_3_AUTONOMOUS:
            decision = ActuationDecision.AUTONOMOUS_ISOLATE
            human_override_requested = True
            message = (f"CRITICAL: Incident {incident_id} on device {device_id}: Tier 3 event. "
            f"Autonomous valve isolation is being triggered NOW. "
            f"Respond within the override window to cancel or confirm.")
            notification_sent = notification_client.send(recipient=operator_contact, message=message,channel="sms", incident_id=incident_id,)
            try:
                valve_command_sent = True
                valve_command_confirmed = actuator_client.isolate(device_id=device_id, incident_id=incident_id)
                trace.append("Tier 3: autonomous valve isolation confirmed by actuator; "
                "human override window now open.")
            except ValveCommandError as exc:
                valve_command_confirmed = False
                logger.error("valve_isolation_FAILED incident_id=%s device_id=%s error=%s",incident_id, device_id, exc,)
                trace.append(f"Tier 3: valve isolation command FAILED to confirm ({exc}). "
                    "Escalating to human operator as an emergency — do not retry blindly.")
                notification_client.send(recipient=operator_contact,
                message=(f"EMERGENCY: Valve isolation for incident {incident_id} FAILED to "
                f"confirm. Immediate manual intervention required."),channel="sms",incident_id=incident_id,)

        else:
            raise ValueError(f"Unsupported severity tier reached execute_response_node: {tier}")
        return {**state,"decision": decision,"notification_sent": notification_sent,"valve_command_sent": valve_command_sent,"valve_command_confirmed": valve_command_confirmed,"human_override_requested": human_override_requested,"reasoning_trace": trace, }
    return execute_response_node

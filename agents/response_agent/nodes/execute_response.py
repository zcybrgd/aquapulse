from __future__ import annotations
import logging
from ..schemas import ActuationDecision
from ..state import ActuationState
from ..tools.actuator_client import ValveActuatorClient, ValveCommandError
from ..tools.notification_client import NotificationClient

logger = logging.getLogger("actuation_agent.nodes.execute_response")


def make_execute_response_node(notification_client: NotificationClient, actuator_client: ValveActuatorClient):
    def execute_response_node(state: ActuationState) -> ActuationState:
        decision: ActuationDecision = state["decision"]
        incident_id = state["incident_id"]
        device_id = state["device_id"]
        operator_contact = state.get("operator_contact", "")
        message = state.get("operator_message", f"Incident {incident_id}: decision={decision}")
        trace = list(state.get("reasoning_trace", []))
        denied = state.get("network_denied")
        notify_channel = denied.fallback.lower() if (denied and denied.fallback != "none") else "sms"
        notification_sent = False
        valve_command_sent = False
        valve_command_confirmed = False
        if decision == ActuationDecision.LOG_ONLY:
            trace.append("Tier 1: logged only, no operator interruption, no network/valve action.")
        elif decision in (ActuationDecision.ALERT_AND_AWAIT, ActuationDecision.ESCALATE_UNREACHABLE):
            notification_sent = notification_client.send(recipient=operator_contact, message=message, channel=notify_channel, incident_id=incident_id,)
            trace.append(f"{decision}: operator notified, no autonomous physical action taken.")
        elif decision == ActuationDecision.AUTONOMOUS_ISOLATE:
            notification_sent = notification_client.send(recipient=operator_contact, message=message, channel=notify_channel, incident_id=incident_id,)
            try:
                valve_command_sent = True
                valve_command_confirmed = actuator_client.isolate(device_id=device_id, incident_id=incident_id)
                trace.append("Tier 3: autonomous valve isolation confirmed by actuator; human override window now open.")
            except ValveCommandError as exc:
                valve_command_confirmed = False
                logger.error("valve_isolation_FAILED incident_id=%s device_id=%s error=%s", incident_id, device_id, exc)
                trace.append(f"Tier 3: valve isolation FAILED to confirm ({exc}). Escalating as emergency — do not retry blindly.")
                notification_client.send(recipient=operator_contact,message=f"EMERGENCY: Valve isolation for incident {incident_id} FAILED to confirm. Manual intervention required.",channel=notify_channel, incident_id=incident_id,)
        else:
            raise ValueError(f"Unsupported decision reached execute_response_node: {decision}")
        return {**state, "notification_sent": notification_sent,"valve_command_sent": valve_command_sent,"valve_command_confirmed": valve_command_confirmed, "reasoning_trace": trace, }

    return execute_response_node
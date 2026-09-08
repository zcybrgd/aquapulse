# Response Agent Documentation

## Overview

The Response Agent is the third stage in the three agent pipeline (Investigation Agent, Network Agent, Response Agent) that reacts to detected pipeline leak incidents in the AquaPulse system. Its job is narrow and safety critical: given a severity tier for an incident and a device to act on, it decides what to do (log it, alert a human, or autonomously close a valve), it checks that the target device can actually be reached before sending any command, it executes that decision through real network calls, it gives a human operator a window to override an autonomous action, and it writes an immutable audit record of everything that happened.

The whole thing is built as a LangGraph state graph, meaning it is a sequence of nodes that all read from and write to one shared state dictionary, executed in a fixed linear order. There is no branching inside the graph itself, all conditional logic (what to do for tier 1 vs tier 3, what to do if the device is unreachable) happens inside individual nodes, mainly llm_response_planner.

Below, every file is documented as a component. For each node the inputs it reads from state, the outputs it writes back to state, and the reasoning behind its behavior are explained. For each tool client, the external service it talks to and why that service exists is explained.

## Why this architecture

### Why LangGraph and a shared state object

Because this is a linear pipeline with strict ordering requirements (you must never send a physical command before you check reachability, you must never skip audit logging), a graph of single purpose nodes threaded through one shared `ActuationState` object gives three properties that matter for a safety system: every node is independently testable, the full history of what happened to an incident is visible at every step through `reasoning_trace`, and adding new nodes (for example a second approval step) later does not require touching unrelated node code.

### Why an LLM is involved at all, and why it is not trusted alone

The `llm_response_planner` node calls an LLM to propose the actuation decision and to draft the human readable operator notification message. The LLM is used for exactly two things it is good at, natural language judgment and natural language generation, not for anything that requires guaranteed correctness.

Reasons an LLM helps here:
- Drafting a clear, incident specific SMS length message for a human operator is a natural language generation task. Writing this by hand for every possible combination of tier, device, and signal quality would be tedious, and templated text reads as robotic.
- The LLM can incorporate incident specific facts (signal quality, whether a network grant is active) into its reasoning in a way that is more legible to a human reviewing the audit log than a lookup table would be.

Reasons the LLM is never allowed to have the final word:
- LLMs can hallucinate or misread the policy, and in a system that can physically close a valve in the desert, a wrong autonomous action or a missed escalation has real consequences.
- The `_enforce_guardrails` function in `llm_response_planner.py` recomputes the decision deterministically from `severity_tier` and `reachable` using a plain dictionary lookup, and if the LLM's proposal does not match what the guardrail computes, the guardrail's answer always wins and the override is written into `reasoning_trace` so it is visible in the audit trail.
- If the LLM call fails outright (timeout, API error, malformed output) the node catches the exception and falls back to a fully rule based decision (`_enforce_guardrails` seeded with `LOG_ONLY`) plus a canned operator message from `_FALLBACK_MESSAGES`. The safety relevant path of the system never depends on the LLM being available.

### Why reachability is checked immediately before acting

`ReachabilityStatus` in `schemas.py` states explicitly that reachability is checked immediately before any command is sent, not earlier, because a device can go from reachable to unreachable between the moment an anomaly is detected upstream and the moment this agent is ready to act. Checking early and trusting a stale result could mean sending a valve close command into the void with no confirmation, which is treated as an emergency (see `ValveCommandError`). `reachability_check` is therefore the very first node in the graph, run fresh for every incident.

### Why the reachability client fails closed

In `reachability_client.py`, any network level failure (timeout, connection error, bad JSON, non 2xx after retries) is caught and turned into `ReachabilityStatus(reachable=False)` rather than raising an exception up the stack or defaulting to `reachable=True`. This is a fail closed design: if the agent cannot confirm a device is reachable, it treats it as unreachable, which downstream forces an `ESCALATE_UNREACHABLE` decision (never fire a command blind) rather than risking a false autonomous action on a device the agent actually cannot see.

### Why the human override window exists

For `AUTONOMOUS_ISOLATE` decisions, the valve is closed immediately (the physical safety action happens without waiting on a person), but a human is simultaneously notified and given a window (`override_window_seconds`) to either confirm the action was correct or override it. This reflects the real world requirement described in `SeverityTier.TIER_3_AUTONOMOUS`: autonomous valve isolation plus a simultaneous human alert. The system does not wait for permission before protecting the pipeline, but it never removes the human from the loop either. If nobody responds in time the outcome is recorded as `timed_out` and the autonomous action stands, logged for retroactive review, it is not silently forgotten.

### Why there is a hard ceiling on severity tier

`ActuationResult.enforce_ceiling` in `schemas.py` is a defensive validator that rejects any raw integer severity value greater than `TIER_3_AUTONOMOUS` (3) before it can even be coerced into the enum. This is a belt and suspenders check against a malformed or malicious upstream payload trying to request a tier of action that does not exist in this agent's policy.

### Why an append only JSONL audit sink

`jsonl_audit_sink` in `graph.py` appends one JSON line per incident to a file rather than overwriting or updating records. Combined with `AuditLogEntry` capturing the full `ActuationResult`, the network grant or denial, and the reasoning trace, this gives a permanent, non destructive record suitable for compliance review of every autonomous action the system ever took. In production this sink is meant to be swapped for a real append only log store or database table, the interface (`Callable[[AuditLogEntry], None]`) is injected so that swap requires no changes to `audit_writer.py` itself.

### Why QoD (Quality on Demand)

QoD is a CAMARA network API standard exposed here through Nokia's Network as Code (NaC) platform. It lets an application reserve a guaranteed quality of service session (bandwidth, latency) over a mobile network for a specific device and application server, for a limited duration. In this system, `NetworkGrant.guarantee_type` can be `"QoD"` or `"slice"`, meaning the upstream Network Agent (not shown in these files but referenced by the graph) has reserved a temporary network guarantee for the affected cluster so that the reachability check, the notification, and the valve command all have a better chance of getting through reliably during a critical incident, rather than competing with ordinary network traffic. `camara-integration/src/clients/qod.py` is the client that actually calls Nokia's `qod.create_session_v1` to reserve that guaranteed session.


## Data Contracts (schemas.py)

These are the Pydantic models that define every payload passed between components. Pydantic validates the data on construction, so if a field is missing or the wrong type, the object fails to build immediately rather than causing a silent bug three nodes later.

### SeverityTier (IntEnum)
The three level scale that drives every branching decision in the system.
- `TIER_1_MONITOR = 1`, log only.
- `TIER_2_ALERT = 2`, alert a human operator and wait.
- `TIER_3_AUTONOMOUS = 3`, autonomously isolate the valve while simultaneously alerting a human.

### NetworkGrant
Emitted upstream by the Network Agent when a network resource request succeeds.
Fields: `cluster_id`, `incident_id`, `severity_tier`, `guarantee_type` (`"QoD"` or `"slice"`), `session_id`, `granted_at`, `expires_at` (optional).

### NetworkDenied
Emitted upstream by the Network Agent when the network request could not be fulfilled, for example due to congestion, a rate cap, or an API failure.
Fields: `cluster_id`, `incident_id`, `severity_tier`, `reason`, `fallback` (`"SMS"` or `"none"`, defaults to `"SMS"`), `denied_at`.

### ReachabilityStatus
The result of one live reachability check, always performed immediately before any command is issued.
Fields: `device_id`, `reachable` (bool), `checked_at`, `raw_signal_quality` (optional string).

### ActuationDecision (str Enum)
The four possible outcomes this agent can reach.
- `LOG_ONLY`
- `ALERT_AND_AWAIT`
- `AUTONOMOUS_ISOLATE`
- `ESCALATE_UNREACHABLE`, used whenever the device cannot be reached, regardless of tier.

### ActuationResult
The complete record of what the agent decided and did for one incident. This is what renders on the dashboard's live reasoning trace and what gets embedded inside the audit log.
Fields: `result_id`, `incident_id`, `cluster_id`, `device_id`, `severity_tier`, `reachability` (a `ReachabilityStatus`), `decision`, `notification_sent` (bool), `valve_command_sent` (bool), `valve_command_confirmed` (bool), `human_override_requested` (bool), `human_override_response` (`"confirmed"`, `"overridden"`, `"timed_out"`, or `None`), `reasoning_trace` (list of strings), `created_at`.


### AuditLogEntry
The top level object actually written to the audit sink.
Fields: `entry_id`, `incident_id`, `cluster_id`, `severity_tier`, `network_grant` (optional), `network_denied` (optional), `actuation_result` (the full `ActuationResult`), `logged_at`.

## Shared State (state.py)

`ActuationState` is a `TypedDict` with `total=False`, meaning every key is optional at the type level, which reflects that the state object is built up incrementally as it flows through the graph, not fully populated at the start.

Inputs, present from the moment the graph is invoked:
`incident_id`, `cluster_id`, `device_id`, `severity_tier`, `network_grant`, `network_denied`, `operator_contact`.

Intermediate fields, filled in by nodes as the incident progresses:
`reachability`, `decision`, `notification_sent`, `valve_command_sent`, `valve_command_confirmed`, `human_override_requested`, `human_override_response`, `reasoning_trace`.

Outputs, filled in at the end:
`audit_entry`, `error`, `operator_message`.

## The Graph (graph.py)

`build_actuation_graph` wires five nodes into a single fixed line, with no conditional edges:

`reachability_check` then `llm_response_planner` then `execute_response` then `human_override` then `audit_writer` then END.

All four external clients (`DeviceReachabilityClient`, `NotificationClient`, `ValveActuatorClient`) and the audit sink and override poller are constructed with sensible defaults if not supplied, but every one of them can be swapped out by the caller. This dependency injection is what makes it possible to run the demo scenarios in `main.py` against local mock servers, and would make it possible to run unit tests with fully fake clients that need no network at all.

`jsonl_audit_sink(path)` is the default audit sink, it appends one JSON line per `AuditLogEntry` to a file (default `audit_log.jsonl`).

`noop_override_poller(incident_id)` is the default override poller, it always returns `None`, meaning by default no override integration is wired up and every autonomous action will simply time out unless a real poller is supplied (the demo in `main.py` supplies one that always returns `"confirmed"`).

## Node by Node Documentation

### 1. reachability_check (reachability_check.py)

Purpose: confirm, right before anything else happens, whether the target device can currently be reached.

Reads from state: `device_id`, `incident_id`.

Calls: `DeviceReachabilityClient.check(device_id)`.

Writes to state: `reachability` (a `ReachabilityStatus`), and appends one line to `reasoning_trace` describing whether the device is confirmed reachable (including its signal quality) or unreachable, in which case the trace explicitly says the agent is escalating to a human rather than firing blind.

Note: a module level instance `reachability_check_node = make_reachability_check_node(DeviceReachabilityClient())` exists at import time using default settings, but `build_actuation_graph` always constructs its own node via `make_reachability_check_node(reachability_client)` using whatever client was passed in or defaulted there, so the injected client is the one actually used in the graph.

### 2. llm_response_planner (llm_response_planner.py)

Purpose: propose an actuation decision and draft the operator facing message using the LLM, then force that proposal through a deterministic guardrail that has final authority.

Reads from state: `reachability`, `severity_tier`, `incident_id`, `device_id`, `network_grant`, `reasoning_trace`.

Calls: the LangChain chain built by `build_llm_decision_chain()`, which is a prompt template piped into `get_groq_llm().with_structured_output(LLMActuationDecision)`. The chain is invoked with `incident_id`, `device_id`, `severity_tier` (as an int), `reachable`, `signal_quality`, and `has_grant` (whether a `network_grant` is present).

LLM output shape (`LLMActuationDecision`): `decision` (an `ActuationDecision`), `operator_message` (SMS length string), `reasoning` (grounded justification using only the given facts, the system prompt explicitly forbids inventing sensor readings or history).

Guardrail logic (`_enforce_guardrails`): if `reachable` is `False`, the decision is always `ESCALATE_UNREACHABLE` regardless of tier. Otherwise the tier maps directly, `TIER_1_MONITOR` to `LOG_ONLY`, `TIER_2_ALERT` to `ALERT_AND_AWAIT`, `TIER_3_AUTONOMOUS` to `AUTONOMOUS_ISOLATE`. If the LLM's proposal differs from this computed value, the guardrail's value replaces it, the fallback message from `_FALLBACK_MESSAGES` replaces the LLM drafted one, and a line is added to `reasoning_trace` recording that the override happened and why.

Failure handling: if the LLM call throws any exception, it is caught, logged, and the node falls back to `_enforce_guardrails(LOG_ONLY, tier, reachable)` (which still correctly escalates or picks the right tier because the guardrail only actually depends on `reachable` and `tier`, the `LOG_ONLY` seed value is discarded whenever `_enforce_guardrails` overrides it) plus the matching canned message from `_FALLBACK_MESSAGES`, and a reasoning trace line noting the LLM failure.

Writes to state: `decision`, `operator_message`, `human_override_requested` (set to `True` only when `decision == AUTONOMOUS_ISOLATE`), and the updated `reasoning_trace`.

### 3. execute_response (execute_response.py)

Purpose: actually carry out the decision, sending notifications and, for tier 3, sending the physical valve command.

Reads from state: `decision`, `incident_id`, `device_id`, `operator_contact`, `operator_message`, `reasoning_trace`.

Calls, branching on `decision`:
- `LOG_ONLY`: no external calls, only a trace line noting no operator interruption and no network or valve action.
- `ALERT_AND_AWAIT` or `ESCALATE_UNREACHABLE`: `NotificationClient.send(recipient=operator_contact, message=operator_message, channel="sms", incident_id=incident_id)`.
- `AUTONOMOUS_ISOLATE`: sends the same notification first, then calls `ValveActuatorClient.isolate(device_id, incident_id)`. If that raises `ValveCommandError` (meaning the actuator did not confirm closure), the failure is logged as an error, a trace line marks it as a failed emergency that must not be retried blindly, and a second, more urgent notification is sent to the operator explicitly stating the isolation failed to confirm and manual intervention is required.
- Any other value raises `ValueError`, since it should be structurally impossible given the guardrail in the previous node.

Writes to state: `notification_sent`, `valve_command_sent`, `valve_command_confirmed`, and the updated `reasoning_trace`.

### 4. human_override (human_override.py)

Purpose: give a human a bounded window to confirm or override an autonomous valve isolation that already happened.

Reads from state: `human_override_requested`, `incident_id`, `reasoning_trace`. If `human_override_requested` is falsy (true for every decision except `AUTONOMOUS_ISOLATE`), the node returns the state unchanged and does nothing else.

Calls: `poll_for_response(incident_id)`, the injected `OverridePoller` function, which the demo in `main.py` sets to always return `"confirmed"` and which defaults to `noop_override_poller` (always `None`) in `graph.py`.

Outcome logic: `None` maps to `"timed_out"` with a trace line noting the window closed without a response and the autonomous action stands for retroactive review. `"overridden"` maps to `"overridden"` with a trace line noting the operator overrode the action. Anything else (for example `"confirmed"`) maps to `"confirmed"` with a trace line noting the operator explicitly confirmed the action.

Writes to state: `human_override_response`, and the updated `reasoning_trace`.

Note: this implementation calls the poller exactly once rather than actually polling repeatedly across `window_seconds` and `poll_interval_seconds`, those two parameters are threaded through and logged but the real polling loop is left to be implemented in a production override poller.

### 5. audit_writer (audit_writer.py)

Purpose: the terminal node, assembles the complete `ActuationResult` and `AuditLogEntry` from everything accumulated in state, then persists it.

Reads from state: `incident_id`, `cluster_id`, `device_id`, `severity_tier`, `reachability`, `decision`, `notification_sent`, `valve_command_sent`, `valve_command_confirmed`, `human_override_requested`, `human_override_response`, `reasoning_trace`, `network_grant`, `network_denied`.

Calls: the injected `sink(entry)` function, either the default `jsonl_audit_sink` writer or, in the demo, a lambda that pretty prints the entry to the console.

Writes to state: `audit_entry` (the full `AuditLogEntry` object).

## Tool Clients

### DeviceReachabilityClient (reachability_client.py)

Talks to `GET {base_url}/v1/device-reachability/{device_id}`, which in the real deployment is the camara integration service described below. Uses a `requests.Session` with automatic retries (`max_retries`, default 2, backoff factor 0.3) on 500, 502, 503, 504 responses for GET requests only. On success returns a `ReachabilityStatus` built from the JSON payload's `reachable` and `signal_quality` fields. On any `RequestException`, `ValueError` (bad JSON), or `KeyError`, it logs a warning and fails closed, returning `reachable=False` rather than propagating the error.

### NotificationClient (notification_client.py)

Talks to `POST {base_url}/v1/notify`, the notification service described below. Uses a `requests.Session` with retries (default `max_retries=3`, backoff factor 0.5) on the same 5xx status codes, for POST requests. `send(recipient, message, channel, incident_id)` returns `True` on success, and on failure logs the error and returns `False` rather than raising, so a notification failure never crashes the graph, it is simply recorded as `notification_sent=False`.

### ValveActuatorClient (actuator_client.py)

Talks to `POST {base_url}/v1/valve/isolate` with `{device_id, incident_id, action: "close"}`. Unlike the other two clients, this one is intentionally strict: any request exception, or a response where the actuator's own payload does not explicitly set `confirmed: true`, raises `ValveCommandError`, a custom exception whose docstring states callers must treat this as an operational emergency. This client never silently swallows a failed physical action, because sending a valve close command and not knowing whether it actually closed is exactly the dangerous ambiguity the whole reachability first design is meant to avoid. On confirmed success it logs at `CRITICAL` level (`VALVE_ISOLATED ...`) since this is a real world physical side effect worth the loudest log level available.



## Entry Point and Demo Scenarios (main.py, response_agent)

`run_scenario` wires up real client instances pointed at whatever local URLs are passed in (defaulting to `localhost:8001/8002/8003` for reachability, notification, and actuator respectively), builds a real LLM chain, and invokes the graph with a freshly constructed `initial_state` for one of five canned scenarios:

`tier1`, `tier2`, `tier3`: the same reachable device (`device-14-valve-A`) at each of the three severity tiers, exercising log only, alert and await, and full autonomous isolate paths.

`unreachable`: a tier 3 incident against `device-offline-demo`, exercising the `ESCALATE_UNREACHABLE` path even though the requested tier would n ormally trigger autonomous action, showing the guardrail overriding tier based on reachability.

`actuator_failure`: a tier 3 incident against `device-14-valve-A-fail`, which the valve actuator simulator is coded to always reject, exercising the `ValveCommandError` emergency escalation path inside `execute_response`.

After invoking the graph, it prints the full `reasoning_trace`, the `operator_message`, and the final `decision`, giving a readable end to end narrative of exactly what the agent decided and why for that one incident.

## End to End Flow Summary

1. An incident arrives with a `severity_tier`, a `device_id`, and optionally a `NetworkGrant` from the upstream Network Agent.
2. `reachability_check` performs a fresh, live reachability check on the device, failing closed to unreachable on any error.
3. `llm_response_planner` asks the LLM to propose a decision and draft an operator message grounded only in the given facts, then a deterministic guardrail recomputes the decision from tier and reachability and overrides the LLM if they disagree, or falls back entirely to rules if the LLM call fails.
4. `execute_response` carries out that decision: nothing for tier 1, an SMS for tier 2 or unreachable, and both an SMS plus a real valve isolate command for tier 3, with a second emergency SMS if the valve fails to confirm.
5. `human_override`, only for autonomous isolations, gives a human a chance to confirm or override the action within a time window, recording a timeout if nobody responds.
6. `audit_writer` assembles everything into an immutable `AuditLogEntry` and persists it, closing out the incident.

Throughout, `reasoning_trace` accumulates a plain English, step by step narrative of every decision and why it was made, which is what ultimately lets a human reviewing the audit log understand, after the fact, exactly why the agent did what it did.



```bash
python -m uvicorn main:app --app-dir notification-service --port 8002 --host 127.0.0.1
python -m uvicorn main:app --app-dir valve-actuator-sim --host 127.0.0.1 --port 8003
python -m uvicorn main:app --app-dir camara-integration/src --port 8001 --host 127.0.0.1
cd agents
python -m response_agent.main --scenario tier1
python -m response_agent.main --scenario tier2
python -m response_agent.main --scenario tier3
python -m response_agent.main --scenario unreachable
python -m response_agent.main --scenario actuator_failure
```
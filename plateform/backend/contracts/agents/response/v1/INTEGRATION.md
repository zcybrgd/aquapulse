# Response Agent contract 1.0

AquaPulse asks for a **recommendation**. It does not ask the agent to execute.

## Endpoints AquaPulse calls

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Bounded liveness |
| GET | `/v1/contract` | Advertise `schema_version: "1.0"` |
| POST | `/v1/recommend-response` | Return a recommended decision |

If the existing graph exposes another path, set `RESPONSE_AGENT_RECOMMEND_PATH`.

## Decisions

`LOG_ONLY`, `ALERT_AND_AWAIT`, `AUTONOMOUS_ISOLATE`, `ESCALATE_UNREACHABLE`.

`AUTONOMOUS_ISOLATE` is still only a recommendation. AquaPulse will not isolate a valve.

## Safety

AquaPulse enforces:

```text
Agent recommendation → validation → human approval → safe execution gateway → verification → audit
```

It does not trust an agent graph that places `execute_response` before `human_override`.

CAMARA QoD is not authorization to actuate a valve.

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from app.integrations.adapters.investigation import parse_investigation_response
from app.integrations.adapters.response import parse_response_result
from app.integrations.constants import CONTRACT_VERSION
from app.integrations.contracts.investigation import InvestigationRequestV1
from app.integrations.contracts.response import ResponseRequestV1
from app.integrations.fixtures import INVESTIGATION_EXAMPLE_REQUEST, RESPONSE_EXAMPLE_REQUEST


@dataclass
class CheckStep:
    name: str
    ok: bool
    detail: str


@dataclass
class ContractCheckResult:
    agent: str
    compatible: bool
    steps: list[CheckStep] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.steps.append(CheckStep(name, ok, detail))


def check_agent_contract(
    agent: str,
    base_url: str,
    *,
    timeout: float = 10,
    transport: httpx.BaseTransport | None = None,
) -> ContractCheckResult:
    result = ContractCheckResult(agent=agent, compatible=True)
    if not base_url.strip():
        result.compatible = False
        result.add("configuration", False, "Base URL is missing.")
        return result

    root = base_url.rstrip("/")
    investigate_path = "/v1/investigate" if agent == "investigation" else "/v1/recommend-response"
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            health = client.get(f"{root}/health")
            result.add("health", health.status_code < 400, f"HTTP {health.status_code}")
            contract = client.get(f"{root}/v1/contract")
            contract_ok = contract.status_code < 400
            version_ok = True
            if contract_ok:
                try:
                    body = contract.json()
                    version = str(body.get("schema_version") or body.get("contract_version") or "")
                    version_ok = version in {"", CONTRACT_VERSION, "1.0"}
                except ValueError:
                    contract_ok = False
                    version_ok = False
            result.add("contract", contract_ok and version_ok, f"HTTP {contract.status_code}")

            fixture = INVESTIGATION_EXAMPLE_REQUEST if agent == "investigation" else RESPONSE_EXAMPLE_REQUEST
            if agent == "investigation":
                InvestigationRequestV1.model_validate(fixture)
            else:
                ResponseRequestV1.model_validate(fixture)
            response = client.post(f"{root}{investigate_path}", json=fixture)
            if response.status_code >= 400:
                result.add("fixture", False, f"HTTP {response.status_code}")
            else:
                try:
                    payload = response.json()
                    if agent == "investigation":
                        parse_investigation_response(payload)
                    else:
                        parse_response_result(payload)
                    result.add("fixture", True, "Response matched contract 1.0")
                except Exception as exc:
                    result.add("fixture", False, str(exc))
    except httpx.TimeoutException:
        result.add("transport", False, "Timed out")
    except httpx.RequestError:
        result.add("transport", False, "Unreachable")

    result.compatible = all(step.ok for step in result.steps)
    return result

from app.core.config import Settings
from app.integrations.clients.investigation import (
    DisabledInvestigationAgentClient,
    HttpInvestigationAgentClient,
    InvestigationAgentClient,
    MockInvestigationAgentClient,
)
from app.integrations.clients.response import (
    DisabledResponseAgentClient,
    HttpResponseAgentClient,
    MockResponseAgentClient,
    ResponseAgentClient,
)


def investigation_client(settings: Settings, *, transport=None) -> InvestigationAgentClient:
    if not settings.agent_integration_enabled or not settings.investigation_agent_enabled:
        return DisabledInvestigationAgentClient()
    mode = settings.investigation_agent_mode
    if mode == "mock":
        return MockInvestigationAgentClient()
    if mode == "remote":
        return HttpInvestigationAgentClient(
            base_url=settings.investigation_agent_url,
            timeout_seconds=settings.investigation_agent_timeout_seconds,
            path=settings.investigation_agent_investigate_path,
            retries=settings.agent_http_max_retries,
            transport=transport,
        )
    return DisabledInvestigationAgentClient()


def response_client(settings: Settings, *, transport=None) -> ResponseAgentClient:
    if not settings.agent_integration_enabled or not settings.response_agent_enabled:
        return DisabledResponseAgentClient()
    mode = settings.response_agent_mode
    if mode == "mock":
        return MockResponseAgentClient()
    if mode == "remote":
        return HttpResponseAgentClient(
            base_url=settings.response_agent_url,
            timeout_seconds=settings.response_agent_timeout_seconds,
            path=settings.response_agent_recommend_path,
            retries=settings.agent_http_max_retries,
            transport=transport,
        )
    return DisabledResponseAgentClient()


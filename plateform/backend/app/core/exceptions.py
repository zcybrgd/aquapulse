class IncidentNotFoundError(Exception):
    def __init__(self, incident_id: str) -> None:
        self.incident_id = incident_id
        super().__init__(f"Incident {incident_id} was not found.")

    @property
    def http_detail(self) -> dict[str, str]:
        return {
            "message": f"Incident {self.incident_id} was not found.",
            "code": "incident_not_found",
        }


class DatabaseUnavailableError(Exception):
    """Raised when PostgreSQL cannot be reached. Do not attach the original driver error."""

    http_detail = {
        "message": "The AquaPulse service cannot reach its database. Try again shortly.",
        "code": "database_unavailable",
    }


class TelemetryValidationError(Exception):
    def __init__(self, message: str, *, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": self.message, "code": self.code}


class DetectionNotFoundError(Exception):
    def __init__(self, detection_id: str) -> None:
        self.detection_id = detection_id
        super().__init__("Detection not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": "Detection not found", "code": "detection_not_found"}


class DetectionConflictError(Exception):
    """Invalid or conflicting detection workflow transition."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        extra: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.extra = extra or {}
        super().__init__(message)

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": self.message, "code": self.code, **self.extra}


class IncidentConflictError(Exception):
    """Invalid or conflicting incident operations transition."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        extra: dict[str, str | int] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.extra = extra or {}
        super().__init__(message)

    @property
    def http_detail(self) -> dict[str, str | int]:
        return {"message": self.message, "code": self.code, **self.extra}


class ResponseTaskNotFoundError(Exception):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__("Response task not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": "Response task not found", "code": "response_task_not_found"}


class AssetValidationError(Exception):
    def __init__(self, message: str, *, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": self.message, "code": self.code}


class AssetNotFoundError(Exception):
    def __init__(self, asset_id: str) -> None:
        self.asset_id = asset_id
        super().__init__("Asset not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": "Asset not found", "code": "asset_not_found"}


class ZoneNotFoundError(Exception):
    def __init__(self, zone: str) -> None:
        self.zone = zone
        super().__init__("Zone not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": f"Zone {self.zone} was not found.", "code": "zone_not_found"}


class AnalyticsValidationError(Exception):
    def __init__(self, message: str, *, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": self.message, "code": self.code}


class MaintenancePlanNotFoundError(Exception):
    def __init__(self, plan_id: str) -> None:
        self.plan_id = plan_id
        super().__init__("Maintenance plan not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": "Maintenance plan not found", "code": "maintenance_plan_not_found"}


class MaintenanceWorkOrderNotFoundError(Exception):
    def __init__(self, work_order_id: str) -> None:
        self.work_order_id = work_order_id
        super().__init__("Maintenance work order not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {
            "message": "Maintenance work order not found",
            "code": "maintenance_work_order_not_found",
        }


class MaintenanceConflictError(Exception):
    """Invalid or conflicting maintenance workflow transition."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        extra: dict[str, str | int] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.extra = extra or {}
        super().__init__(message)

    @property
    def http_detail(self) -> dict[str, str | int]:
        return {"message": self.message, "code": self.code, **self.extra}


class NetworkEventNotFoundError(Exception):
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__("Network event not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": "Network event not found", "code": "network_event_not_found"}


class AgentAuditRunNotFoundError(Exception):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__("Agent audit run not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": "Agent audit run not found", "code": "agent_audit_run_not_found"}


class AgentAuditEventNotFoundError(Exception):
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__("Agent audit event not found")

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": "Agent audit event not found", "code": "agent_audit_event_not_found"}


class AgentIntegrationError(Exception):
    """Structured agent-gateway error. Never attach secrets or remote URLs."""

    def __init__(self, message: str, *, code: str, status_code: int = 422) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

    @property
    def http_detail(self) -> dict[str, str]:
        return {"message": self.message, "code": self.code}

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AgentIntegrationError
from app.integrations.constants import CAMARA_DISABLED_REASON, NOTIFICATIONS_DISABLED_REASON, PHYSICAL_BLOCKED_REASON
from app.integrations.identity import investigation_mapper, response_mapper
from app.repositories.assets import AssetRepository
from app.schemas.integrations import (
    CompatNotifyResponse,
    CompatQodResponse,
    CompatReachability,
    CompatValveIsolateResponse,
    CompatValveStatusResponse,
)


class CompatibilityService:
    """Development compatibility gateway. Never performs real CAMARA, notify, or actuation."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.assets = AssetRepository(session)

    def _resolve_device(self, device_id: str) -> tuple[str | None, str]:
        for mapper in (response_mapper(self.session), investigation_mapper(self.session)):
            for entity_type in ("device", "valve", "sensor"):
                lookup = mapper.resolve(entity_type, device_id)
                if lookup.mapped and lookup.internal_public_id:
                    return lookup.internal_public_id, "mapped"
        asset = self.assets.get_by_external_id(device_id)
        if asset is not None:
            return asset.external_id, "direct"
        return None, "unmapped"

    def reachability(self, device_id: str) -> CompatReachability:
        public_id, mapping_status = self._resolve_device(device_id)
        if public_id is None:
            raise AgentIntegrationError(
                "No configured mapping exists for this device.",
                code="agent_identity_unmapped",
                status_code=422,
            )
        asset = self.assets.get_by_external_id(public_id)
        if asset is None:
            raise AgentIntegrationError(
                "No configured mapping exists for this device.",
                code="agent_identity_unmapped",
                status_code=422,
            )
        reachable = asset.operational_status != "offline"
        return CompatReachability(
            device_id=device_id,
            reachable=reachable,
            checked_at=datetime.now(timezone.utc),
            raw_signal_quality=asset.signal_strength_dbm,
            mapping_status=mapping_status,
            aquapulse_asset_id=asset.external_id,
            data_mode="mock",
        )

    def reserve_qod(self, device_id: str) -> CompatQodResponse:
        _ = device_id
        return CompatQodResponse(
            device_id=device_id,
            reserved=False,
            denied=True,
            reason=CAMARA_DISABLED_REASON,
            data_mode="mock",
            real_network_guarantee=False,
        )

    def notify(self, payload: dict[str, Any]) -> CompatNotifyResponse:
        if not isinstance(payload, dict):
            raise AgentIntegrationError("Notification payload is invalid.", code="agent_invalid_response", status_code=422)
        return CompatNotifyResponse(sent=False, reason=NOTIFICATIONS_DISABLED_REASON, data_mode="mock")

    def isolate_valve(self, payload: dict[str, Any] | None = None) -> CompatValveIsolateResponse:
        _ = payload
        return CompatValveIsolateResponse(
            confirmed=False,
            executed=False,
            status="blocked",
            reason=PHYSICAL_BLOCKED_REASON,
            data_mode="mock",
        )

    def valve_status(self, device_id: str) -> CompatValveStatusResponse:
        public_id, mapping_status = self._resolve_device(device_id)
        if public_id is None:
            raise AgentIntegrationError(
                "No configured mapping exists for this device.",
                code="agent_identity_unmapped",
                status_code=422,
            )
        asset = self.assets.get_by_external_id(public_id)
        if asset is None or asset.asset_type != "valve":
            raise AgentIntegrationError(
                "No configured mapping exists for this valve.",
                code="agent_identity_unmapped",
                status_code=422,
            )
        return CompatValveStatusResponse(
            device_id=device_id,
            aquapulse_valve_id=asset.external_id,
            current_position=asset.current_position,
            mapping_status=mapping_status,
            data_mode="mock",
        )

    def valve_position(self, public_id: str) -> str | None:
        asset = self.assets.get_by_external_id(public_id)
        return asset.current_position if asset else None

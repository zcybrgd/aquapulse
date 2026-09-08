from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select

from app.api.deps import get_device_network_provider
from app.core.config import Settings
from app.core.exceptions import DeviceNetworkProviderError
from app.db.models import Asset
from app.db.models.device_network import DeviceNetworkSnapshot
from app.db.models.integration import AgentRun
from app.db.session import get_session_factory
from app.integrations.sanitize import REDACTED, sanitize_payload
from app.main import app
from app.network.device_network import (
    normalize_location_payload,
    normalize_reachability_payload,
)
from app.network.providers import (
    DisabledDeviceNetworkProvider,
    HttpNokiaDeviceNetworkProvider,
    MockNokiaDeviceNetworkProvider,
    build_device_network_provider,
)
from app.scripts.seed_database import seed_database
from app.scripts.seed_device_network import SEED_SNAPSHOTS


def _session():
    return get_session_factory()()


def _assert_no_raw_msisdn(payload) -> None:
    dumped = json.dumps(payload)
    assert "+971500004821" not in dumped
    assert "+971500007007" not in dumped
    assert '"device_msisdn"' not in dumped


def test_reachability_and_location_normalization() -> None:
    reachable = normalize_reachability_payload(
        {"reachable": True, "connectivity": ["DATA", "SMS"], "lastStatusTime": "2026-09-01T07:00:00Z"}
    )
    assert reachable.status == "reachable"
    assert reachable.reachable_via == "data"
    unreachable = normalize_reachability_payload({"reachable": False, "connectivity": []})
    assert unreachable.status == "unreachable"
    unknown = normalize_reachability_payload({})
    assert unknown.status == "unknown"
    subscription = normalize_reachability_payload({"subscriptionId": "sub-1", "status": "ACTIVE"})
    assert subscription.status == "unknown"
    assert subscription.error_code == "subscription_response_not_state"
    location = normalize_location_payload(
        {
            "lastLocationTime": "2026-09-01T07:00:00Z",
            "area": {"areaType": "CIRCLE", "center": {"latitude": 25.2, "longitude": 55.3}, "radius": 800},
        }
    )
    assert location.available is True
    assert location.latitude == 25.2
    assert location.accuracy_radius_m == 800
    missing = normalize_location_payload({"area": {"areaType": "CIRCLE"}})
    assert missing.available is False


def test_mock_and_disabled_providers() -> None:
    async def run() -> None:
        mock = MockNokiaDeviceNetworkProvider(source_mode="seeded_demo")
        data = await mock.get_reachability("+971500004821")
        sms = await mock.get_reachability("+971500000201")
        down = await mock.get_reachability("+971500007007")
        unknown = await mock.get_reachability("+971500000221")
        located = await mock.retrieve_location("+971500004821")
        missing = await mock.retrieve_location("+971500007007")
        assert data.status == "reachable" and data.reachable_via == "data"
        assert sms.reachable_via == "sms"
        assert down.status == "unreachable"
        assert unknown.status == "unknown"
        assert located.available is True and located.accuracy_radius_m == 420
        assert missing.available is False
        disabled = DisabledDeviceNetworkProvider()
        skipped = await disabled.get_reachability("+971500004821")
        assert skipped.status == "not_checked"
        assert skipped.error_code == "provider_disabled"

    asyncio.run(run())


def test_http_provider_mocked_transport_timeout_and_malformed() -> None:
    settings = Settings(
        nokia_network_api_enabled=True,
        nokia_network_api_mode="live",
        nokia_network_api_base_url="https://nokia.example.test",
        nokia_network_api_key="test-key-not-real",
        nokia_network_api_host="nokia.example.test",
        nokia_network_timeout_seconds=1,
        nokia_network_max_retries=1,
    )

    def success(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-RapidAPI-Key"] == "test-key-not-real"
        body = json.loads(request.content)
        assert body["device"]["phoneNumber"].startswith("+")
        if "reachability" in str(request.url):
            return httpx.Response(200, json={"reachable": True, "connectivity": ["SMS"]})
        return httpx.Response(
            200,
            json={
                "area": {"areaType": "CIRCLE", "center": {"latitude": 25.1, "longitude": 55.2}, "radius": 500}
            },
        )

    async def run() -> None:
        provider = HttpNokiaDeviceNetworkProvider(settings, transport=httpx.MockTransport(success))
        reach = await provider.get_reachability("+971500004821")
        location = await provider.retrieve_location("+971500004821")
        assert reach.status == "reachable"
        assert reach.reachable_via == "sms"
        assert location.available is True
        assert location.accuracy_radius_m == 500

        def timeout(_request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("slow")

        timed = HttpNokiaDeviceNetworkProvider(settings, transport=httpx.MockTransport(timeout))
        try:
            await timed.get_reachability("+971500004821")
            raise AssertionError("expected timeout")
        except DeviceNetworkProviderError as exc:
            assert exc.code == "nokia_timeout"

        def malformed(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not-json")

        bad = HttpNokiaDeviceNetworkProvider(settings, transport=httpx.MockTransport(malformed))
        try:
            await bad.retrieve_location("+971500004821")
            raise AssertionError("expected malformed")
        except DeviceNetworkProviderError as exc:
            assert exc.code == "nokia_malformed_response"

    asyncio.run(run())


def test_factory_defaults_to_mock_without_credentials() -> None:
    settings = Settings(nokia_network_api_enabled=False, nokia_network_api_mode="mock")
    provider = build_device_network_provider(settings)
    assert isinstance(provider, MockNokiaDeviceNetworkProvider)
    assert provider.source_mode == "seeded_demo"
    live_without_key = Settings(
        nokia_network_api_enabled=True,
        nokia_network_api_mode="live",
        nokia_network_api_base_url="",
        nokia_network_api_key="",
    )
    fallback = build_device_network_provider(live_without_key)
    assert isinstance(fallback, MockNokiaDeviceNetworkProvider)
    disabled = build_device_network_provider(Settings(nokia_network_api_mode="disabled"))
    assert isinstance(disabled, DisabledDeviceNetworkProvider)


def test_devices_with_and_without_msisdn(client, test_database) -> None:
    cellular = client.get("/api/network-health/devices", params={"cellular_available": True}).json()
    none = client.get("/api/network-health/devices", params={"cellular_available": False}).json()
    assert cellular["total"] >= 1
    assert none["total"] >= 1
    assert all(item["has_cellular_identity"] for item in cellular["items"])
    assert all(not item["has_cellular_identity"] for item in none["items"])
    valve = client.get("/api/network-health/devices/VLV-CRN-014").json()
    assert valve["has_cellular_identity"] is False
    assert valve["device_msisdn_masked"] is None
    assert valve["reachability_status"] == "not_supported"
    refreshed = client.post("/api/network-health/devices/VLV-CRN-014/refresh").json()
    assert refreshed["reachability_status"] == "not_supported"
    assert refreshed["error_code"] == "msisdn_required"
    _assert_no_raw_msisdn(cellular)
    _assert_no_raw_msisdn(valve)
    _assert_no_raw_msisdn(refreshed)


def test_latest_snapshot_filters_and_summary(client, test_database) -> None:
    summary = client.get("/api/network-health/summary").json()
    assert summary["cellular_devices"] >= 1
    assert summary["reachable"] >= 1
    assert summary["unreachable"] >= 1
    assert summary["unknown_or_not_checked"] >= 1
    assert summary["network_location_available"] >= 1
    assert summary["stale_checks"] >= 0
    assert summary["environment_label"] == "Demonstration environment"
    assert "grants" not in summary
    harbour = client.get("/api/network-health/devices", params={"zone": "Harbour"}).json()
    assert harbour["total"] >= 1
    assert all("Harbour" in (item["zone_name"] or "") for item in harbour["items"])
    gateways = client.get("/api/network-health/devices", params={"asset_type": "gateway"}).json()
    assert all(item["asset_type"] == "gateway" for item in gateways["items"])
    reachable = client.get("/api/network-health/devices", params={"reachability": "reachable"}).json()
    assert all(item["reachability_status"] == "reachable" for item in reachable["items"])
    located = client.get("/api/network-health/devices", params={"location_available": True}).json()
    assert all(item["network_location_available"] for item in located["items"])
    gateway = client.get("/api/network-health/devices/HBR-GW-02").json()
    assert gateway["accuracy_radius_m"] == 420
    assert gateway["network_location_available"] is True
    assert gateway["history"]
    history = client.get("/api/network-health/devices/HBR-GW-02/history").json()
    assert history[0]["snapshot_id"].startswith("DNS-")
    missing = client.get("/api/network-health/devices/MISSING-DEVICE")
    assert missing.status_code == 404


def test_cache_and_force_refresh(client, test_database) -> None:
    first = client.post("/api/network-health/devices/HBR-GW-02/refresh").json()
    second = client.post("/api/network-health/devices/HBR-GW-02/refresh").json()
    assert second["cached"] is True
    assert second["snapshot_id"] == first["snapshot_id"]
    forced = client.post("/api/network-health/devices/HBR-GW-02/refresh", json={"force": True}).json()
    assert forced["cached"] is False
    assert forced["snapshot_id"] != first["snapshot_id"]


def test_bulk_refresh_is_bounded(client, test_database) -> None:
    payload = client.post("/api/network-health/refresh", json={"force": True, "limit": 3}).json()
    assert payload["requested"] == 3
    assert payload["succeeded"] + payload["failed"] + payload["skipped_cached"] == 3
    _assert_no_raw_msisdn(payload)


def test_bulk_refresh_concurrency_limit(client, test_database) -> None:
    class CountingProvider:
        provider_name = "nokia_mock"
        source_mode = "seeded_demo"
        current = 0
        max_seen = 0

        async def get_reachability(self, device_msisdn: str):
            self.current += 1
            self.max_seen = max(self.max_seen, self.current)
            await asyncio.sleep(0.05)
            self.current -= 1
            return normalize_reachability_payload({"reachable": True, "connectivity": ["DATA"]})

        async def retrieve_location(self, device_msisdn: str):
            return normalize_location_payload(
                {"area": {"areaType": "CIRCLE", "center": {"latitude": 25.0, "longitude": 55.0}, "radius": 100}}
            )

    provider = CountingProvider()
    app.dependency_overrides[get_device_network_provider] = lambda: provider
    try:
        response = client.post(
            "/api/network-health/refresh",
            json={"force": True, "asset_ids": ["HBR-GW-02", "CRN-GW-01", "DOH-GW-02", "JED-GW-01"], "limit": 4},
        )
        assert response.status_code == 200
        assert provider.max_seen <= 4
        assert provider.max_seen >= 1
    finally:
        app.dependency_overrides.pop(get_device_network_provider, None)


def test_sanitization_and_no_key_leak(client, test_database) -> None:
    cleaned = sanitize_payload(
        {
            "phoneNumber": "+971500004821",
            "X-RapidAPI-Key": "secret",
            "Authorization": "Bearer secret",
            "safe": "ok",
        }
    )
    assert cleaned["phoneNumber"] == REDACTED
    assert cleaned["X-RapidAPI-Key"] == REDACTED
    assert cleaned["Authorization"] == REDACTED
    summary = client.get("/api/network-health/summary").json()
    devices = client.get("/api/network-health/devices").json()
    dumped = json.dumps({"summary": summary, "devices": devices})
    assert "NOKIA_NETWORK_API_KEY" not in dumped
    assert "test-key" not in dumped
    _assert_no_raw_msisdn(devices)


def test_incident_network_context_uses_stored_snapshot(client, test_database) -> None:
    class ForbiddenProvider:
        provider_name = "forbidden"
        source_mode = "seeded_demo"

        async def get_reachability(self, device_msisdn: str):
            raise AssertionError("incident list must not call Nokia")

        async def retrieve_location(self, device_msisdn: str):
            raise AssertionError("incident list must not call Nokia")

    app.dependency_overrides[get_device_network_provider] = lambda: ForbiddenProvider()
    try:
        listed = client.get("/api/incidents").json()
        assert listed["total"] == 9
        context = client.get("/api/incidents/INC-1835/device-network").json()
        assert context["available"] is True
        assert context["asset_id"]
        assert "investigating" not in (context["reachability_status"] or "")
        _assert_no_raw_msisdn(context)
    finally:
        app.dependency_overrides.pop(get_device_network_provider, None)


def test_refresh_does_not_execute_agents_or_change_valves(client, test_database) -> None:
    session = _session()
    runs_before = session.scalar(select(func.count()).select_from(AgentRun))
    valve_before = session.scalar(select(Asset.current_position).where(Asset.external_id == "VLV-CRN-014"))
    session.close()
    client.post("/api/network-health/devices/HBR-GW-02/refresh", json={"force": True})
    session = _session()
    runs_after = session.scalar(select(func.count()).select_from(AgentRun))
    valve_after = session.scalar(select(Asset.current_position).where(Asset.external_id == "VLV-CRN-014"))
    session.close()
    assert runs_before == runs_after
    assert valve_before == valve_after
    incidents = client.get("/api/incidents").json()
    assert incidents["total"] == 9


def test_seed_idempotent_and_compatibility(client, test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.device_network_snapshots == second.device_network_snapshots == 9
    session = _session()
    public_ids = set(
        session.scalars(
            select(DeviceNetworkSnapshot.public_id).where(
                DeviceNetworkSnapshot.public_id.in_([item["public_id"] for item in SEED_SNAPSHOTS])
            )
        )
    )
    session.close()
    assert public_ids == {item["public_id"] for item in SEED_SNAPSHOTS}
    events = client.get("/api/network-health/events").json()
    assert events["total"] == 0
    assert client.get("/api/network-health/events/NETEVT-000004").status_code == 404
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/incidents").status_code == 200
    assert client.get("/api/assets").status_code == 200
    assert client.get("/api/agent-audit/summary").status_code == 200


def test_snapshot_constraints_and_persistence(test_database) -> None:
    session = _session()
    row = session.scalar(select(DeviceNetworkSnapshot).where(DeviceNetworkSnapshot.public_id == "DNS-000001"))
    assert row is not None
    assert row.network_location_available is True
    assert -90 <= row.network_latitude <= 90
    assert row.accuracy_radius_m >= 0
    unsupported = session.scalar(select(DeviceNetworkSnapshot).where(DeviceNetworkSnapshot.public_id == "DNS-000005"))
    assert unsupported.reachability_status == "not_supported"
    assert unsupported.network_location_available is False
    stale = session.scalar(select(DeviceNetworkSnapshot).where(DeviceNetworkSnapshot.public_id == "DNS-000009"))
    assert stale.retrieved_at < datetime.now(timezone.utc)
    session.close()

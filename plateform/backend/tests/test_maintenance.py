from datetime import timedelta
from threading import Thread

from sqlalchemy import select

from app.data.incidents import SEED_NOW
from app.db.models import Asset
from app.db.models.maintenance import MaintenancePlan, MaintenanceWorkOrder, MaintenanceWorkOrderEvent
from app.db.session import get_session_factory
from app.integrations.constants import CONTRACT_VERSION
from app.scripts.generate_maintenance_work_orders import generate
from app.scripts.seed_database import seed_database
from app.services.maintenance import REFERENCE_TIME

ACTOR = {"actor_name": "Demo Operator"}


def _restore() -> None:
    seed_database()


def test_seeded_maintenance_shapes(test_database) -> None:
    session = get_session_factory()()
    try:
        plans = list(session.scalars(select(MaintenancePlan)).all())
        orders = list(session.scalars(select(MaintenanceWorkOrder)).all())
        assert len(plans) == 9
        assert len(orders) == 6
        assert {item.public_id for item in orders} == {
            "MWO-000001",
            "MWO-000002",
            "MWO-000003",
            "MWO-000004",
            "MWO-000005",
            "MWO-000006",
        }
        statuses = {item.public_id: item.status for item in orders}
        assert statuses["MWO-000001"] == "scheduled"
        assert statuses["MWO-000003"] == "assigned"
        assert statuses["MWO-000004"] == "in_progress"
        assert statuses["MWO-000005"] == "completed"
        assert statuses["MWO-000006"] == "cancelled"
        overdue = next(item for item in orders if item.public_id == "MWO-000001")
        assert overdue.due_at < REFERENCE_TIME
        assert overdue.priority == "critical"
        assert overdue.incident_id is not None
        due_soon = next(item for item in orders if item.public_id == "MWO-000002")
        assert REFERENCE_TIME < due_soon.due_at <= REFERENCE_TIME + timedelta(days=7)
        assert any(not item.enabled for item in plans)
        planned_assets = {item.asset_id for item in plans if item.enabled}
        unplanned = session.scalar(select(Asset).where(Asset.external_id == "SNS-RUH-078"))
        assert unplanned is not None
        assert unplanned.id not in planned_assets
    finally:
        session.close()


def test_seed_maintenance_is_idempotent(test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.maintenance_plans == second.maintenance_plans == 9
    assert first.maintenance_work_orders == second.maintenance_work_orders == 6
    assert first.assets == second.assets == 35


def test_plan_create_update_disable_and_interval(client, test_database) -> None:
    created = client.post(
        "/api/maintenance/plans",
        json={
            **ACTOR,
            "asset_id": "SNS-RUH-078",
            "name": "Industrial ring preventive",
            "maintenance_type": "preventive",
            "interval_days": 30,
            "priority": "medium",
            "next_due_at": (SEED_NOW + timedelta(days=15)).isoformat(),
        },
    )
    assert created.status_code == 200
    plan_id = created.json()["public_id"]
    assert plan_id.startswith("MPLAN-")

    invalid = client.post(
        "/api/maintenance/plans",
        json={
            **ACTOR,
            "asset_id": "SNS-RUH-078",
            "name": "Bad interval",
            "maintenance_type": "inspection",
            "interval_days": 0,
            "next_due_at": SEED_NOW.isoformat(),
        },
    )
    assert invalid.status_code == 422

    updated = client.patch(
        f"/api/maintenance/plans/{plan_id}",
        json={**ACTOR, "interval_days": 45, "priority": "high"},
    )
    assert updated.status_code == 200
    assert updated.json()["interval_days"] == 45
    assert updated.json()["priority"] == "high"

    disabled = client.post(f"/api/maintenance/plans/{plan_id}/disable", json=ACTOR)
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    _restore()


def test_work_order_lifecycle_and_history(client, test_database) -> None:
    created = client.post(
        "/api/maintenance/work-orders",
        json={
            **ACTOR,
            "asset_id": "SNS-RUH-078",
            "maintenance_type": "inspection",
            "title": "Industrial ring pit check",
            "priority": "medium",
            "due_at": (SEED_NOW + timedelta(days=2)).isoformat(),
        },
    )
    assert created.status_code == 200
    work_id = created.json()["public_id"]
    assert work_id.startswith("MWO-")
    assert created.json()["status"] == "scheduled"
    assert created.json()["overdue"] is False

    assigned = client.post(
        f"/api/maintenance/work-orders/{work_id}/assign",
        json={**ACTOR, "assigned_to": "Fatima Al Hashimi"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"
    assert assigned.json()["assigned_to"] == "Fatima Al Hashimi"

    reassigned = client.post(
        f"/api/maintenance/work-orders/{work_id}/assign",
        json={**ACTOR, "assigned_to": "Demo Operator"},
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["assigned_to"] == "Demo Operator"

    rescheduled = client.post(
        f"/api/maintenance/work-orders/{work_id}/reschedule",
        json={**ACTOR, "due_at": (SEED_NOW + timedelta(days=5)).isoformat()},
    )
    assert rescheduled.status_code == 200

    noted = client.post(
        f"/api/maintenance/work-orders/{work_id}/notes",
        json={**ACTOR, "note": "Status must stay assigned."},
    )
    assert noted.status_code == 200
    assert noted.json()["status"] == "assigned"

    started = client.post(f"/api/maintenance/work-orders/{work_id}/start", json=ACTOR)
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert started.json()["started_at"] is not None

    missing_complete = client.post(
        f"/api/maintenance/work-orders/{work_id}/complete",
        json={**ACTOR, "completion_result": "completed_successfully", "completion_summary": "Done"},
    )
    assert missing_complete.status_code == 409
    assert missing_complete.json()["detail"]["code"] == "maintenance_completion_required"

    completed = client.post(
        f"/api/maintenance/work-orders/{work_id}/complete",
        json={
            **ACTOR,
            "completion_result": "completed_successfully",
            "completion_summary": "Pit inspected. No physical command executed.",
            "confirm": True,
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    history = client.get(f"/api/maintenance/work-orders/{work_id}/history").json()
    types = [item["event_type"] for item in history["items"]]
    assert types[0] == "work_order_created"
    assert "work_order_assigned" in types
    assert "note_added" in types
    assert types[-1] == "work_completed"
    timestamps = [item["created_at"] for item in history["items"]]
    assert timestamps == sorted(timestamps)

    assert client.post(f"/api/maintenance/work-orders/{work_id}/start", json=ACTOR).status_code == 409
    _restore()


def test_start_requires_assignment_or_confirmation(client, test_database) -> None:
    blocked = client.post("/api/maintenance/work-orders/MWO-000001/start", json=ACTOR)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "maintenance_assignment_required"

    started = client.post(
        "/api/maintenance/work-orders/MWO-000001/start",
        json={**ACTOR, "confirm_unassigned": True},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    _restore()


def test_cancel_requires_reason_and_confirmation(client, test_database) -> None:
    missing = client.post(
        "/api/maintenance/work-orders/MWO-000002/cancel",
        json={**ACTOR, "reason": "Not needed"},
    )
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "maintenance_cancellation_reason_required"

    cancelled = client.post(
        "/api/maintenance/work-orders/MWO-000002/cancel",
        json={**ACTOR, "reason": "Crew diverted to INC-1842.", "confirm": True},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancellation_reason"]
    _restore()


def test_overdue_and_filters(client, test_database) -> None:
    summary = client.get("/api/maintenance/summary").json()
    assert summary["overdue"] >= 1
    assert summary["due_within_7_days"] >= 1
    assert summary["in_progress"] >= 1
    assert summary["critical"] >= 1
    assert summary["assets_without_plan"] >= 1
    assert summary["reference_time"].startswith("2026-09-01T07:45:00")

    overdue = client.get("/api/maintenance/work-orders", params={"overdue": True}).json()
    assert overdue["total"] >= 1
    assert all(item["overdue"] for item in overdue["items"])
    assert all(item["status"] not in {"completed", "cancelled"} for item in overdue["items"])

    zone = client.get("/api/maintenance/work-orders", params={"zone": "Corniche DMA"}).json()
    assert any(item["asset_id"] == "VLV-CRN-014" for item in zone["items"])

    asset = client.get("/api/maintenance/work-orders", params={"asset_id": "HBR-GW-02"}).json()
    assert all(item["asset_id"] == "HBR-GW-02" for item in asset["items"])

    listed = client.get("/api/assets").json()
    assert listed["total"] == 35


def test_unknown_ids_and_public_ids(client, test_database) -> None:
    missing_order = client.get("/api/maintenance/work-orders/MWO-999999")
    assert missing_order.status_code == 404
    assert missing_order.json()["detail"]["code"] == "maintenance_work_order_not_found"

    missing_plan = client.get("/api/maintenance/plans/MPLAN-999999")
    assert missing_plan.status_code == 404
    assert missing_plan.json()["detail"]["code"] == "maintenance_plan_not_found"

    missing_asset = client.get("/api/assets/SNS-NONE/maintenance")
    assert missing_asset.status_code == 404
    assert missing_asset.json()["detail"]["code"] == "asset_not_found"

    detail = client.get("/api/maintenance/work-orders/MWO-000001").json()
    assert detail["id"] == "MWO-000001"
    assert "uuid" not in detail["id"].lower()
    assert detail["incident_id"] == "INC-1842"


def test_completion_updates_asset_dates_not_status(client, test_database) -> None:
    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
        assert asset is not None
        previous_status = asset.operational_status
        previous_position = asset.current_position
    finally:
        session.close()

    client.post("/api/maintenance/work-orders/MWO-000001/start", json={**ACTOR, "assigned_to": "Demo Operator"})
    completed = client.post(
        "/api/maintenance/work-orders/MWO-000001/complete",
        json={
            **ACTOR,
            "completion_result": "asset_repaired",
            "completion_summary": "Chamber inspected and recorded. No valve command sent.",
            "confirm": True,
        },
    )
    assert completed.status_code == 200

    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
        assert asset is not None
        assert asset.operational_status == previous_status
        assert asset.current_position == previous_position
        assert asset.last_maintenance_at is not None
    finally:
        session.close()

    incident = client.get("/api/incidents/INC-1842").json()
    assert incident["status"] != "resolved"
    _restore()


def test_follow_up_does_not_change_asset_dates(client, test_database) -> None:
    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).where(Asset.external_id == "HBR-GW-02"))
        previous = asset.last_maintenance_at
    finally:
        session.close()

    completed = client.post(
        "/api/maintenance/work-orders/MWO-000004/complete",
        json={
            **ACTOR,
            "completion_result": "follow_up_required",
            "completion_summary": "Uplink still intermittent.",
            "confirm": True,
        },
    )
    assert completed.status_code == 200
    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).where(Asset.external_id == "HBR-GW-02"))
        assert asset.last_maintenance_at == previous
    finally:
        session.close()
    _restore()


def test_asset_and_incident_maintenance_endpoints(client, test_database) -> None:
    asset = client.get("/api/assets/VLV-CRN-014/maintenance").json()
    assert asset["asset_id"] == "VLV-CRN-014"
    assert asset["overdue"] is True
    assert any(item["public_id"] == "MWO-000001" for item in asset["open_work_orders"])

    related = client.get("/api/incidents/INC-1842/maintenance").json()
    assert related["incident_id"] == "INC-1842"
    assert related["total"] >= 1
    assert related["items"][0]["incident_id"] == "INC-1842"


def test_generator_is_idempotent(test_database) -> None:
    first = generate(as_of=SEED_NOW)
    assert first["created"] >= 1
    second = generate(as_of=SEED_NOW)
    assert second["created"] == 0
    session = get_session_factory()()
    try:
        generated = session.scalar(select(MaintenanceWorkOrder).where(MaintenanceWorkOrder.public_id == "MWO-000007"))
        assert generated is not None
        assert generated.status == "scheduled"
        assert generated.started_at is None
        events = list(session.scalars(select(MaintenanceWorkOrderEvent)).all())
        assert all(item.event_type != "work_started" for item in events if item.work_order_id == generated.id)
    finally:
        session.close()
    _restore()


def test_disabled_plan_does_not_generate(client, test_database) -> None:
    disabled = client.get("/api/maintenance/plans/MPLAN-000009").json()
    assert disabled["enabled"] is False
    generate(as_of=SEED_NOW)
    listed = client.get("/api/maintenance/work-orders", params={"asset_id": "SNS-DOH-044"}).json()
    assert listed["total"] == 0
    _restore()


def test_duplicate_open_order_from_plan(client, test_database) -> None:
    conflict = client.post(
        "/api/maintenance/work-orders",
        json={
            **ACTOR,
            "asset_id": "SNS-HBR-007",
            "maintenance_plan_id": "MPLAN-000001",
            "maintenance_type": "preventive",
            "title": "Duplicate Harbour preventive",
            "due_at": (SEED_NOW + timedelta(days=1)).isoformat(),
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "maintenance_duplicate_open_order"


def test_unknown_asset_on_create(client, test_database) -> None:
    response = client.post(
        "/api/maintenance/work-orders",
        json={
            **ACTOR,
            "asset_id": "SNS-NONE",
            "maintenance_type": "inspection",
            "title": "Missing",
            "due_at": SEED_NOW.isoformat(),
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "asset_not_found"


def test_concurrent_start_protection(client, test_database) -> None:
    results: list[int] = []

    def worker() -> None:
        results.append(
            client.post(
                "/api/maintenance/work-orders/MWO-000003/start",
                json=ACTOR,
            ).status_code
        )

    first = Thread(target=worker)
    second = Thread(target=worker)
    first.start()
    second.start()
    first.join()
    second.join()
    assert 200 in results
    detail = client.get("/api/maintenance/work-orders/MWO-000003").json()
    assert detail["status"] == "in_progress"
    _restore()


def test_transaction_rollback_on_invalid_complete(client, test_database) -> None:
    client.post("/api/maintenance/work-orders/MWO-000002/notes", json={**ACTOR, "note": "Keep scheduled."})
    failed = client.post(
        "/api/maintenance/work-orders/MWO-000002/complete",
        json={
            **ACTOR,
            "completion_result": "completed_successfully",
            "completion_summary": "Too early.",
            "confirm": True,
        },
    )
    assert failed.status_code == 409
    detail = client.get("/api/maintenance/work-orders/MWO-000002").json()
    assert detail["status"] == "scheduled"
    assert detail["completed_at"] is None


def test_agent_contract_and_existing_assets_remain_compatible(client, test_database) -> None:
    assert CONTRACT_VERSION == "1.0"
    asset = client.get("/api/assets/HBR-GW-02").json()
    assert asset["external_id"] == "HBR-GW-02"
    assert asset["zone_id"] == "ZONE-HBR"
    assert "device_msisdn" not in asset or asset.get("device_msisdn") is None
    assert client.get("/api/incidents/INC-1842").status_code == 200

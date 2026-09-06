"""Idempotent Maintenance Center demonstration data.

Uses existing asset and incident public IDs. Does not change geometry, MSISDN,
or agent contracts.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.incidents import SEED_NOW
from app.db.models import Asset, Incident
from app.db.models.maintenance import MaintenancePlan, MaintenanceWorkOrder, MaintenanceWorkOrderEvent

DEMO_OPERATOR = "Demo Operator"
DEMO_TECHNICIAN = "Fatima Al Hashimi"
DEMO_SUPERVISOR = "Demo Supervisor"
DEMO_PLANS = {f"MPLAN-{index:06d}" for index in range(1, 10)}
DEMO_ORDERS = {f"MWO-{index:06d}" for index in range(1, 7)}
DEMO_EVENTS = {f"MWE-{index:06d}" for index in range(1, 9)} | {f"MWE-P{index:06d}" for index in range(1, 10)}


def _asset(session: Session, external_id: str) -> Asset:
    asset = session.scalar(select(Asset).where(Asset.external_id == external_id))
    if asset is None:
        raise RuntimeError(f"Seed asset {external_id} is missing")
    return asset


def _incident(session: Session, number: str) -> Incident | None:
    return session.scalar(select(Incident).where(Incident.incident_number == number))


def _get_or_create_plan(session: Session, public_id: str, values: dict) -> MaintenancePlan:
    instance = session.scalar(select(MaintenancePlan).filter_by(public_id=public_id))
    if instance is None:
        instance = MaintenancePlan(id=uuid4(), public_id=public_id, **values)
        session.add(instance)
        session.flush()
        return instance
    for key, value in values.items():
        setattr(instance, key, value)
    return instance


_ORDER_DEFAULTS = {
    "maintenance_plan_id": None,
    "incident_id": None,
    "description": None,
    "assigned_to": None,
    "scheduled_start_at": None,
    "started_at": None,
    "completed_at": None,
    "completed_by": None,
    "completion_result": None,
    "completion_summary": None,
    "cancelled_at": None,
    "cancelled_by": None,
    "cancellation_reason": None,
}


def _get_or_create_order(session: Session, public_id: str, values: dict) -> MaintenanceWorkOrder:
    payload = {**_ORDER_DEFAULTS, **values}
    instance = session.scalar(select(MaintenanceWorkOrder).filter_by(public_id=public_id))
    if instance is None:
        instance = MaintenanceWorkOrder(id=uuid4(), public_id=public_id, **payload)
        session.add(instance)
        session.flush()
        return instance
    for key, value in payload.items():
        setattr(instance, key, value)
    session.flush()
    return instance


def _add_event(
    session: Session,
    *,
    public_id: str,
    work_order: MaintenanceWorkOrder | None = None,
    plan: MaintenancePlan | None = None,
    event_type: str,
    actor_name: str,
    created_at,
    from_status: str | None = None,
    to_status: str | None = None,
    note: str | None = None,
) -> None:
    existing = session.scalar(select(MaintenanceWorkOrderEvent).filter_by(public_id=public_id))
    if existing is not None:
        return
    session.add(
        MaintenanceWorkOrderEvent(
            id=uuid4(),
            public_id=public_id,
            work_order_id=work_order.id if work_order is not None else None,
            plan_id=plan.id if plan is not None else (work_order.maintenance_plan_id if work_order else None),
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_name=actor_name,
            note=note,
            extra_metadata={"demo": True},
            created_at=created_at,
        )
    )
    session.flush()


def seed_maintenance_demo(session: Session) -> None:
    extra_events = session.scalars(
        select(MaintenanceWorkOrderEvent).where(MaintenanceWorkOrderEvent.public_id.not_in(DEMO_EVENTS))
    ).all()
    for event in extra_events:
        session.delete(event)
    extra_orders = session.scalars(
        select(MaintenanceWorkOrder).where(MaintenanceWorkOrder.public_id.not_in(DEMO_ORDERS))
    ).all()
    for order in extra_orders:
        session.delete(order)
    extra_plans = session.scalars(
        select(MaintenancePlan).where(MaintenancePlan.public_id.not_in(DEMO_PLANS))
    ).all()
    for plan in extra_plans:
        session.delete(plan)
    session.flush()

    harbour_sensor = _asset(session, "SNS-HBR-007")
    corniche_valve = _asset(session, "VLV-CRN-014")
    harbour_gateway = _asset(session, "HBR-GW-02")
    corniche_sensor = _asset(session, "SNS-CRN-014")
    corniche_gateway = _asset(session, "CRN-GW-01")
    ain_sensor = _asset(session, "SNS-AIN-221")
    harbour_valve = _asset(session, "VLV-HBR-007")
    jeddah_sensor = _asset(session, "SNS-JED-112")
    ain_gateway = _asset(session, "AIN-GW-01")
    doha_sensor = _asset(session, "SNS-DOH-044")
    leak = _incident(session, "INC-1842")

    plans = {
        "MPLAN-000001": _get_or_create_plan(
            session,
            "MPLAN-000001",
            {
                "asset_id": harbour_sensor.id,
                "name": "Harbour cluster preventive inspection",
                "maintenance_type": "preventive",
                "interval_days": 90,
                "priority": "high",
                "instructions": "Inspect Harbour transfer multi-sensor cluster and confirm chamber seals.",
                "enabled": True,
                "next_due_at": SEED_NOW + timedelta(days=4),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000002": _get_or_create_plan(
            session,
            "MPLAN-000002",
            {
                "asset_id": corniche_valve.id,
                "name": "Corniche isolation valve inspection",
                "maintenance_type": "inspection",
                "interval_days": 30,
                "priority": "critical",
                "instructions": "Verify isolation valve position and chamber access after leak response.",
                "enabled": True,
                "next_due_at": SEED_NOW + timedelta(days=20),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000003": _get_or_create_plan(
            session,
            "MPLAN-000003",
            {
                "asset_id": harbour_gateway.id,
                "name": "Harbour gateway connectivity check",
                "maintenance_type": "connectivity_check",
                "interval_days": 14,
                "priority": "medium",
                "instructions": "Confirm LTE uplink, packet delivery and cabinet power.",
                "enabled": True,
                "next_due_at": SEED_NOW + timedelta(days=20),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000004": _get_or_create_plan(
            session,
            "MPLAN-000004",
            {
                "asset_id": corniche_sensor.id,
                "name": "Corniche pressure sensor calibration",
                "maintenance_type": "calibration",
                "interval_days": 180,
                "priority": "medium",
                "instructions": "Calibrate pressure range against the chamber reference gauge.",
                "enabled": True,
                "next_due_at": SEED_NOW + timedelta(days=60),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000005": _get_or_create_plan(
            session,
            "MPLAN-000005",
            {
                "asset_id": corniche_gateway.id,
                "name": "Corniche gateway battery replacement",
                "maintenance_type": "battery_replacement",
                "interval_days": 365,
                "priority": "low",
                "instructions": "Replace cabinet backup battery and record the serial.",
                "enabled": True,
                "next_due_at": SEED_NOW + timedelta(days=90),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000006": _get_or_create_plan(
            session,
            "MPLAN-000006",
            {
                "asset_id": harbour_valve.id,
                "name": "Harbour isolation valve preventive cycle",
                "maintenance_type": "preventive",
                "interval_days": 45,
                "priority": "high",
                "instructions": "Exercise the isolation valve and inspect the chamber.",
                "enabled": True,
                "next_due_at": SEED_NOW - timedelta(days=1),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000007": _get_or_create_plan(
            session,
            "MPLAN-000007",
            {
                "asset_id": jeddah_sensor.id,
                "name": "Obhur feeder inspection",
                "maintenance_type": "inspection",
                "interval_days": 60,
                "priority": "medium",
                "instructions": "Walk the Obhur Node 12 pit and photograph fittings.",
                "enabled": True,
                "next_due_at": SEED_NOW + timedelta(days=10),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000008": _get_or_create_plan(
            session,
            "MPLAN-000008",
            {
                "asset_id": ain_gateway.id,
                "name": "Al Ain gateway connectivity check",
                "maintenance_type": "connectivity_check",
                "interval_days": 21,
                "priority": "medium",
                "instructions": "Confirm tower uplink and cabinet temperature.",
                "enabled": True,
                "next_due_at": SEED_NOW + timedelta(days=14),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
        "MPLAN-000009": _get_or_create_plan(
            session,
            "MPLAN-000009",
            {
                "asset_id": doha_sensor.id,
                "name": "Lusail preventive plan (disabled)",
                "maintenance_type": "preventive",
                "interval_days": 90,
                "priority": "low",
                "instructions": "Disabled demonstration plan. Do not generate work.",
                "enabled": False,
                "next_due_at": SEED_NOW - timedelta(days=2),
                "created_by": DEMO_SUPERVISOR,
            },
        ),
    }

    for public_id, plan in plans.items():
        _add_event(
            session,
            public_id=f"MWE-P{public_id[-6:]}",
            plan=plan,
            event_type="plan_created" if plan.enabled else "plan_disabled",
            actor_name=DEMO_SUPERVISOR,
            created_at=SEED_NOW - timedelta(days=40),
            note="Seeded demonstration plan.",
        )

    overdue = _get_or_create_order(
        session,
        "MWO-000001",
        {
            "asset_id": corniche_valve.id,
            "maintenance_plan_id": plans["MPLAN-000002"].id,
            "incident_id": leak.id if leak is not None else None,
            "maintenance_type": "corrective",
            "title": "Corniche isolation valve post-leak inspection",
            "description": "Critical follow-up after INC-1842. Confirm the valve chamber and isolation integrity.",
            "priority": "critical",
            "status": "scheduled",
            "due_at": SEED_NOW - timedelta(days=3),
            "created_by": DEMO_SUPERVISOR,
        },
    )
    due_soon = _get_or_create_order(
        session,
        "MWO-000002",
        {
            "asset_id": harbour_sensor.id,
            "maintenance_plan_id": plans["MPLAN-000001"].id,
            "maintenance_type": "preventive",
            "title": "Harbour cluster preventive inspection",
            "description": "Due within seven days of the demonstration clock.",
            "priority": "high",
            "status": "scheduled",
            "due_at": SEED_NOW + timedelta(days=4),
            "created_by": DEMO_SUPERVISOR,
        },
    )
    assigned = _get_or_create_order(
        session,
        "MWO-000003",
        {
            "asset_id": corniche_sensor.id,
            "maintenance_plan_id": plans["MPLAN-000004"].id,
            "maintenance_type": "inspection",
            "title": "Corniche trunk chamber inspection",
            "description": "Assigned field inspection of the KM 4.2 chamber.",
            "priority": "medium",
            "status": "assigned",
            "assigned_to": DEMO_TECHNICIAN,
            "due_at": SEED_NOW + timedelta(days=10),
            "created_by": DEMO_SUPERVISOR,
        },
    )
    in_progress = _get_or_create_order(
        session,
        "MWO-000004",
        {
            "asset_id": harbour_gateway.id,
            "maintenance_plan_id": plans["MPLAN-000003"].id,
            "maintenance_type": "connectivity_check",
            "title": "Harbour gateway connectivity check",
            "description": "Technician is on site confirming the LTE uplink.",
            "priority": "medium",
            "status": "in_progress",
            "assigned_to": DEMO_TECHNICIAN,
            "started_at": SEED_NOW - timedelta(hours=3),
            "due_at": SEED_NOW + timedelta(days=1),
            "created_by": DEMO_SUPERVISOR,
        },
    )
    completed = _get_or_create_order(
        session,
        "MWO-000005",
        {
            "asset_id": corniche_gateway.id,
            "maintenance_plan_id": plans["MPLAN-000005"].id,
            "maintenance_type": "battery_replacement",
            "title": "Corniche gateway battery replacement",
            "description": "Completed demonstration replacement of the cabinet backup battery.",
            "priority": "low",
            "status": "completed",
            "assigned_to": DEMO_OPERATOR,
            "started_at": SEED_NOW - timedelta(days=12),
            "due_at": SEED_NOW - timedelta(days=10),
            "completed_at": SEED_NOW - timedelta(days=10),
            "completed_by": DEMO_OPERATOR,
            "completion_result": "completed_successfully",
            "completion_summary": "Backup battery replaced. No physical command was sent to the gateway.",
            "created_by": DEMO_SUPERVISOR,
        },
    )
    cancelled = _get_or_create_order(
        session,
        "MWO-000006",
        {
            "asset_id": ain_sensor.id,
            "maintenance_type": "calibration",
            "title": "Al Ain feeder calibration (cancelled)",
            "description": "Cancelled after the chamber was found inaccessible.",
            "priority": "low",
            "status": "cancelled",
            "due_at": SEED_NOW - timedelta(days=6),
            "cancelled_at": SEED_NOW - timedelta(days=5),
            "cancelled_by": DEMO_SUPERVISOR,
            "cancellation_reason": "Chamber access blocked by civil works. Reschedule after clearance.",
            "created_by": DEMO_SUPERVISOR,
        },
    )

    _add_event(
        session,
        public_id="MWE-000001",
        work_order=overdue,
        plan=plans["MPLAN-000002"],
        event_type="work_order_created",
        actor_name=DEMO_SUPERVISOR,
        created_at=SEED_NOW - timedelta(days=8),
        to_status="scheduled",
        note="Created after INC-1842 for the Corniche isolation valve.",
    )
    _add_event(
        session,
        public_id="MWE-000002",
        work_order=due_soon,
        plan=plans["MPLAN-000001"],
        event_type="work_order_created",
        actor_name=DEMO_SUPERVISOR,
        created_at=SEED_NOW - timedelta(days=6),
        to_status="scheduled",
        note="Preventive cycle for the Harbour cluster.",
    )
    _add_event(
        session,
        public_id="MWE-000003",
        work_order=assigned,
        event_type="work_order_created",
        actor_name=DEMO_SUPERVISOR,
        created_at=SEED_NOW - timedelta(days=4),
        to_status="scheduled",
    )
    _add_event(
        session,
        public_id="MWE-000004",
        work_order=assigned,
        event_type="work_order_assigned",
        actor_name=DEMO_SUPERVISOR,
        created_at=SEED_NOW - timedelta(days=3),
        from_status="scheduled",
        to_status="assigned",
        note=f"Assigned to {DEMO_TECHNICIAN}",
    )
    _add_event(
        session,
        public_id="MWE-000005",
        work_order=in_progress,
        event_type="work_order_created",
        actor_name=DEMO_SUPERVISOR,
        created_at=SEED_NOW - timedelta(days=2),
        to_status="assigned",
    )
    _add_event(
        session,
        public_id="MWE-000006",
        work_order=in_progress,
        event_type="work_started",
        actor_name=DEMO_TECHNICIAN,
        created_at=SEED_NOW - timedelta(hours=3),
        from_status="assigned",
        to_status="in_progress",
        note="Arrived at Harbour Pump Station 2.",
    )
    _add_event(
        session,
        public_id="MWE-000007",
        work_order=completed,
        event_type="work_completed",
        actor_name=DEMO_OPERATOR,
        created_at=SEED_NOW - timedelta(days=10),
        from_status="in_progress",
        to_status="completed",
        note="Backup battery replaced. No physical command was sent to the gateway.",
    )
    _add_event(
        session,
        public_id="MWE-000008",
        work_order=cancelled,
        event_type="work_cancelled",
        actor_name=DEMO_SUPERVISOR,
        created_at=SEED_NOW - timedelta(days=5),
        from_status="scheduled",
        to_status="cancelled",
        note="Chamber access blocked by civil works. Reschedule after clearance.",
    )

    corniche_gateway.last_maintenance_at = SEED_NOW - timedelta(days=10)
    harbour_valve.next_maintenance_at = plans["MPLAN-000006"].next_due_at

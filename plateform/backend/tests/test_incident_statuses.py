from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Incident, IncidentTimelineEvent
from app.db.session import get_session_factory
from app.incident.workflow import LEGACY_INCIDENT_STATUS_MAP, migrate_incident_status
from app.integrations.constants import DECISIONS
from app.integrations.contracts.response import ResponseResultV1
from app.scripts.seed_database import seed_database

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_ROOT.parent / "frontend" / "src"
MIGRATION = BACKEND_ROOT / "alembic" / "versions" / "0012_incident_statuses.py"

CURRENT_STATUSES = {"investigating", "awaiting_approval", "resolved"}
LEGACY_FILTERS = ("open", "acknowledged", "responding", "monitoring", "false_alarm")


def test_legacy_status_mapping_covers_every_known_value() -> None:
    expected = {
        "open": "investigating",
        "acknowledged": "investigating",
        "investigating": "investigating",
        "responding": "investigating",
        "monitoring": "investigating",
        "awaiting_approval": "awaiting_approval",
        "resolved": "resolved",
        "false_alarm": "resolved",
    }
    assert LEGACY_INCIDENT_STATUS_MAP == expected
    for old, new in expected.items():
        assert migrate_incident_status(old) == new
        assert new in CURRENT_STATUSES


def test_migration_rewrites_every_legacy_status() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "0012_incident_statuses" in source
    assert len("0012_incident_statuses") < 32
    for old in ("open", "acknowledged", "responding", "monitoring", "false_alarm"):
        assert f"WHEN '{old}'" in source or f"WHEN status = '{old}'" in source
    assert "investigating" in source
    assert "awaiting_approval" in source
    assert "resolved" in source
    assert "COALESCE(resolution_code, 'false_alarm')" in source
    assert "ck_incidents_status_allowed" in source


def test_database_accepts_only_three_incident_statuses(test_database) -> None:
    session = get_session_factory()()
    try:
        row = session.scalar(select(Incident).where(Incident.incident_number == "INC-1838"))
        assert row is not None
        for status in CURRENT_STATUSES:
            if status == "resolved":
                continue
            row.status = status
            session.flush()
        row.status = "open"
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_legacy_status_filters_return_422(client, test_database) -> None:
    for value in LEGACY_FILTERS:
        listing = client.get("/api/incidents", params={"status": value})
        assert listing.status_code == 422, value
        queue = client.get("/api/operations/queue", params={"status": value})
        assert queue.status_code == 422, value
        mapped = client.get("/api/map/incidents", params={"incident_status": value})
        assert mapped.status_code == 422, value


def test_current_status_filters_are_accepted(client, test_database) -> None:
    for value in CURRENT_STATUSES:
        response = client.get("/api/incidents", params={"status": value})
        assert response.status_code == 200, value
        assert all(item["status"] == value for item in response.json()["items"])


def test_new_and_promoted_incidents_start_investigating(client, test_database) -> None:
    listing = client.get("/api/incidents").json()["items"]
    created = [item for item in listing if item["id"] in {"INC-1838", "INC-1840", "INC-1836"}]
    assert created
    assert all(item["status"] == "investigating" for item in created)


def test_active_and_resolved_summary_calculations(client, test_database) -> None:
    dashboard = client.get("/api/dashboard/summary").json()
    queue = client.get("/api/operations/queue").json()["summary"]
    listing = client.get("/api/incidents").json()["items"]
    investigating = [item for item in listing if item["status"] == "investigating"]
    awaiting = [item for item in listing if item["status"] == "awaiting_approval"]
    resolved = [item for item in listing if item["status"] == "resolved"]
    assert dashboard["active_incidents"] == len(investigating) + len(awaiting) == 7
    assert queue["investigating"] == len(investigating)
    assert queue["awaiting_approval"] == len(awaiting) == 1
    assert len(resolved) == 2
    assert dashboard["responding"] == 1
    assert queue["responding"] == 1


def test_historical_timeline_is_preserved(client, test_database) -> None:
    before = client.get("/api/incidents/INC-1842/timeline").json()["events"]
    catalog_ids = [event["id"] for event in before if event["id"].startswith("INC-1842-evt-")]
    assert "INC-1842-evt-1" in catalog_ids
    client.post("/api/incidents/INC-1842/notes", json={"actor_name": "Demo Operator", "note": "Keep history."})
    after = client.get("/api/incidents/INC-1842/timeline").json()["events"]
    remaining = {event["id"] for event in after}
    assert set(catalog_ids) <= remaining
    session = get_session_factory()()
    try:
        incident = session.scalar(select(Incident).where(Incident.incident_number == "INC-1842"))
        events = list(session.scalars(select(IncidentTimelineEvent).where(IncidentTimelineEvent.incident_id == incident.id)))
        assert len(events) == len(after)
    finally:
        session.close()
    seed_database()


def test_seeded_false_alarm_keeps_resolution_code(test_database) -> None:
    session = get_session_factory()()
    try:
        row = session.scalar(select(Incident).where(Incident.incident_number == "INC-1837"))
        assert row is not None
        assert row.status == "resolved"
        assert row.resolution_code == "false_alarm"
        assert row.resolution_summary
        assert row.resolved_at
        assert row.evidence
    finally:
        session.close()


def test_creating_a_task_does_not_start_response(client, test_database) -> None:
    before = client.get("/api/incidents/INC-1842/operations").json()
    created = client.post(
        "/api/incidents/INC-1842/tasks",
        json={"actor_name": "Demo Operator", "title": "Planning only"},
    )
    assert created.status_code == 200
    after = client.get("/api/incidents/INC-1842/operations").json()
    assert after["status"] == "investigating"
    assert after["response_started_at"] == before["response_started_at"]
    seed_database()


def test_agent_decision_schema_is_unchanged() -> None:
    assert DECISIONS == (
        "LOG_ONLY",
        "ALERT_AND_AWAIT",
        "AUTONOMOUS_ISOLATE",
        "ESCALATE_UNREACHABLE",
    )
    field = ResponseResultV1.model_fields["decision"]
    assert "ALERT_AND_AWAIT" in str(field.annotation)
    assert "AUTONOMOUS_ISOLATE" in str(field.annotation)


def test_frontend_hides_estimated_loss_and_legacy_status_labels() -> None:
    forbidden = (
        "Estimated water loss",
        "Est. loss",
        "EST. LOSS",
        "Estimated loss",
        "Agents still working the case",
        "Awaiting approval",
    )
    matches: list[str] = []
    for path in FRONTEND_SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            if phrase in text:
                matches.append(f"{path.relative_to(FRONTEND_SRC)}: {phrase}")
    assert matches == []

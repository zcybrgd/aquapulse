from threading import Thread

from sqlalchemy import select

from app.db.models import Incident
from app.db.session import get_session_factory
from app.scripts.seed_database import seed_database
from tests.test_investigation import (
    SEEDED_INCIDENTS,
    _cleanup_promoted_incidents,
    _prepare_detections,
    _review,
)

ACTOR = {"actor_name": "Demo Operator"}


def _restore() -> None:
    seed_database()


def _session():
    return get_session_factory()()


def test_acknowledge_assign_and_note(client, test_database) -> None:
    first = client.post("/api/incidents/INC-1838/acknowledge", json={**ACTOR, "note": "Control room ack."})
    assert first.status_code == 200
    assert first.json()["status"] == "acknowledged"
    assert first.json()["acknowledged_by"] == "Demo Operator"

    repeat = client.post("/api/incidents/INC-1838/acknowledge", json=ACTOR)
    assert repeat.status_code == 200
    assert repeat.json()["status"] == "acknowledged"

    assigned = client.post(
        "/api/incidents/INC-1838/assign",
        json={**ACTOR, "assigned_to": "Harbour Response Team", "note": "Field check."},
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned_to"] == "Harbour Response Team"

    note = client.post("/api/incidents/INC-1838/notes", json={**ACTOR, "note": "No status change expected."})
    assert note.status_code == 200
    assert note.json()["status"] == "acknowledged"
    _restore()


def test_valid_and_invalid_incident_transitions(client, test_database) -> None:
    assert client.post("/api/incidents/INC-1838/start-investigation", json=ACTOR).status_code == 409
    assert client.post("/api/incidents/INC-1838/start-response", json=ACTOR).status_code == 409
    assert client.post("/api/incidents/INC-1838/resolve", json={
        **ACTOR,
        "resolution_code": "other",
        "resolution_summary": "Too early.",
    }).status_code == 409

    client.post("/api/incidents/INC-1838/acknowledge", json=ACTOR)
    started = client.post("/api/incidents/INC-1838/start-investigation", json=ACTOR)
    assert started.status_code == 200
    assert started.json()["status"] == "investigating"

    approval = client.post("/api/incidents/INC-1838/request-approval", json=ACTOR)
    assert approval.status_code == 200
    assert approval.json()["status"] == "awaiting_approval"

    returned = client.post("/api/incidents/INC-1838/start-investigation", json=ACTOR)
    assert returned.status_code == 200
    assert returned.json()["status"] == "investigating"

    client.post("/api/incidents/INC-1838/assign", json={**ACTOR, "assigned_to": "Demo Operator"})
    responding = client.post("/api/incidents/INC-1838/start-response", json=ACTOR)
    assert responding.status_code == 200
    assert responding.json()["status"] == "responding"

    assert client.post("/api/incidents/INC-1838/false-alarm", json={
        **ACTOR,
        "resolution_summary": "Not allowed from responding.",
    }).status_code == 409

    resolved = client.post(
        "/api/incidents/INC-1838/resolve",
        json={**ACTOR, "resolution_code": "monitoring_completed", "resolution_summary": "Returned to range."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    assert client.post("/api/incidents/INC-1838/notes", json={**ACTOR, "note": "Closed."}).status_code == 409
    reopened = client.post("/api/incidents/INC-1838/reopen", json={**ACTOR, "note": "New telemetry."})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert reopened.json()["resolution_code"] is None
    _restore()


def test_false_alarm_and_resolution_requirements(client, test_database) -> None:
    missing = client.post(
        "/api/incidents/INC-1833/resolve",
        json={**ACTOR, "resolution_code": "leak_repaired", "resolution_summary": "   "},
    )
    assert missing.status_code == 422

    marked = client.post(
        "/api/incidents/INC-1833/false-alarm",
        json={**ACTOR, "resolution_summary": "Sensor noise, not a leak. History is retained."},
    )
    assert marked.status_code == 200
    assert marked.json()["status"] == "false_alarm"
    assert marked.json()["resolution_code"] == "false_alarm"

    already = client.post(
        "/api/incidents/INC-1834/resolve",
        json={**ACTOR, "resolution_code": "other", "resolution_summary": "Already closed."},
    )
    assert already.status_code == 409
    assert already.json()["detail"]["code"] == "incident_already_terminal"
    _restore()


def test_start_response_requires_assignment(client, test_database) -> None:
    client.post("/api/incidents/INC-1838/acknowledge", json=ACTOR)
    client.post("/api/incidents/INC-1838/start-investigation", json=ACTOR)
    blocked = client.post("/api/incidents/INC-1838/start-response", json=ACTOR)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "incident_assignment_required"
    _restore()


def test_response_task_lifecycle_and_invalid_transitions(client, test_database) -> None:
    created = client.post(
        "/api/incidents/INC-1842/tasks",
        json={**ACTOR, "title": "Confirm crew briefing", "priority": "high"},
    )
    assert created.status_code == 200
    task_id = created.json()["public_id"]
    assert task_id.startswith("TASK-")
    assert created.json()["status"] == "todo"

    edited = client.patch(
        f"/api/incidents/INC-1842/tasks/{task_id}",
        json={**ACTOR, "title": "Confirm crew briefing and radios", "priority": "critical"},
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "Confirm crew briefing and radios"

    started = client.post(f"/api/incidents/INC-1842/tasks/{task_id}/start", json=ACTOR)
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"

    assert client.post(f"/api/incidents/INC-1842/tasks/{task_id}/start", json=ACTOR).status_code == 409

    completed = client.post(
        f"/api/incidents/INC-1842/tasks/{task_id}/complete",
        json={**ACTOR, "completion_note": "Briefing complete. No valve command sent."},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_by"] == "Demo Operator"

    assert client.patch(
        f"/api/incidents/INC-1842/tasks/{task_id}",
        json={**ACTOR, "title": "Should fail"},
    ).status_code == 409

    cancelled_source = client.post(
        "/api/incidents/INC-1842/tasks",
        json={**ACTOR, "title": "Spare radio check"},
    ).json()["public_id"]
    cancelled = client.post(f"/api/incidents/INC-1842/tasks/{cancelled_source}/cancel", json=ACTOR)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(
        f"/api/incidents/INC-1842/tasks/{cancelled_source}/complete",
        json=ACTOR,
    ).status_code == 409

    assert client.get("/api/incidents/INC-0000/tasks").status_code == 404
    assert client.post(
        "/api/incidents/INC-1842/tasks/TASK-999999/start",
        json=ACTOR,
    ).status_code == 404
    _restore()


def test_tasks_rejected_outside_responding(client, test_database) -> None:
    blocked = client.post(
        "/api/incidents/INC-1838/tasks",
        json={**ACTOR, "title": "Should not exist"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "invalid_incident_transition"


def test_resolve_with_incomplete_tasks(client, test_database) -> None:
    conflict = client.post(
        "/api/incidents/INC-1842/resolve",
        json={
            **ACTOR,
            "resolution_code": "monitoring_completed",
            "resolution_summary": "Network returned to range.",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "incident_incomplete_tasks"
    assert conflict.json()["detail"]["incomplete_task_count"] >= 1

    confirmed = client.post(
        "/api/incidents/INC-1842/resolve",
        json={
            **ACTOR,
            "resolution_code": "monitoring_completed",
            "resolution_summary": "Network returned to range.",
            "confirm_incomplete_tasks": True,
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "resolved"
    _restore()


def test_blank_actor_is_validation_error(client, test_database) -> None:
    response = client.post("/api/incidents/INC-1838/acknowledge", json={"actor_name": "   "})
    assert response.status_code == 422


def test_unknown_ids(client, test_database) -> None:
    assert client.get("/api/incidents/INC-0000/operations").status_code == 404
    assert client.post("/api/incidents/INC-0000/acknowledge", json=ACTOR).status_code == 404


def test_timeline_appends_and_orders(client, test_database) -> None:
    before = client.get("/api/incidents/INC-1838/timeline").json()["events"]
    client.post("/api/incidents/INC-1838/acknowledge", json={**ACTOR, "note": "Ack from test."})
    after = client.get("/api/incidents/INC-1838/timeline").json()["events"]
    assert len(after) == len(before) + 1
    assert after[-1]["event_type"] == "incident_acknowledged"
    assert after[-1]["actor_name"] == "Demo Operator"
    stamps = [event["timestamp"] for event in after]
    assert stamps == sorted(stamps)
    _restore()


def test_operations_queue_and_dashboard_counts(client, test_database) -> None:
    queue = client.get("/api/operations/queue")
    assert queue.status_code == 200
    payload = queue.json()
    assert payload["summary"]["active_incidents"] == 7
    assert payload["summary"]["unacknowledged"] >= 1
    assert payload["summary"]["awaiting_approval"] == 1
    assert payload["summary"]["responding"] == 1
    assert payload["summary"]["overdue_tasks"] >= 1
    assert any(item["id"] == "INC-1838" for item in payload["items"])
    assert payload["overdue_tasks"]

    dashboard = client.get("/api/dashboard/summary")
    assert dashboard.status_code == 200
    assert dashboard.json()["active_incidents"] == 7
    assert dashboard.json()["awaiting_approval"] == 1
    assert dashboard.json()["responding"] == 1
    assert dashboard.json()["overdue_response_tasks"] >= 1


def test_existing_incident_apis_remain_compatible(client, test_database) -> None:
    listing = client.get("/api/incidents")
    assert listing.status_code == 200
    assert listing.json()["total"] == 9
    assert {item["id"] for item in listing.json()["items"]} == SEEDED_INCIDENTS
    detail = client.get("/api/incidents/INC-1835")
    assert detail.status_code == 200
    assert detail.json()["title"]
    assert len(detail.json()["telemetry"]) == 16


def test_seed_idempotency_keeps_incident_count(client, test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.incidents == second.incidents == 9
    session = _session()
    try:
        statuses = {
            row.incident_number: row.status
            for row in session.scalars(select(Incident)).all()
        }
    finally:
        session.close()
    assert statuses["INC-1838"] == "open"
    assert statuses["INC-1836"] == "acknowledged"
    assert statuses["INC-1835"] == "awaiting_approval"
    assert statuses["INC-1842"] == "responding"
    assert statuses["INC-1834"] == "resolved"


def test_promoted_detection_uses_operations_workflow(client, test_database) -> None:
    numbers = _prepare_detections(client)
    source = numbers[0]
    _review(client, source)
    promoted = client.post(
        f"/api/detections/{source}/promote",
        json={
            **ACTOR,
            "title": "Promoted harbour check",
            "severity": "tier_2",
            "classification": "suspected_leak",
            "summary": "Promoted for operations workflow test.",
        },
    )
    assert promoted.status_code == 200
    incident_id = promoted.json()["incident"]["id"]
    ops = client.get(f"/api/incidents/{incident_id}/operations")
    assert ops.status_code == 200
    assert ops.json()["status"] == "investigating"
    assert "add_note" in ops.json()["allowed_actions"]
    note = client.post(f"/api/incidents/{incident_id}/notes", json={**ACTOR, "note": "From promotion."})
    assert note.status_code == 200
    assert note.json()["status"] == "investigating"
    _cleanup_promoted_incidents()
    _restore()


def test_concurrent_start_response_protection(client, test_database) -> None:
    results: list[int] = []

    def worker() -> None:
        response = client.post("/api/incidents/INC-1841/start-response", json=ACTOR)
        results.append(response.status_code)

    first = Thread(target=worker)
    second = Thread(target=worker)
    first.start()
    second.start()
    first.join()
    second.join()
    assert sorted(results) == [200, 409]
    _restore()

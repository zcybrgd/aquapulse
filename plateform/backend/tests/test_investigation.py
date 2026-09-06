from threading import Thread

from sqlalchemy import delete, select

from app.db.models import AnomalyDetection, DetectionEvidence, Incident, IncidentTimelineEvent
from app.db.models.response_task import IncidentResponseTask
from app.db.session import get_session_factory
from app.detection.engine import DetectionEngine
from tests.test_detections import _cleanup_detections, _ingest_scenario, _unique_end
from datetime import timedelta

ACTOR = {"actor_name": "Demo Operator"}
SEEDED_INCIDENTS = {
    "INC-1833",
    "INC-1834",
    "INC-1835",
    "INC-1836",
    "INC-1837",
    "INC-1838",
    "INC-1840",
    "INC-1841",
    "INC-1842",
}


def _session():
    return get_session_factory()()


def _cleanup_promoted_incidents() -> None:
    session = _session()
    try:
        extras = list(
            session.scalars(select(Incident).where(Incident.incident_number.notin_(SEEDED_INCIDENTS))).all()
        )
        extra_ids = [incident.id for incident in extras]
        if extra_ids:
            linked = list(
                session.scalars(select(AnomalyDetection).where(AnomalyDetection.incident_id.in_(extra_ids))).all()
            )
            for row in linked:
                row.status = "new"
                row.incident_id = None
                row.resolved_at = None
            session.flush()
        for incident in extras:
            session.execute(delete(IncidentTimelineEvent).where(IncidentTimelineEvent.incident_id == incident.id))
            session.execute(delete(IncidentResponseTask).where(IncidentResponseTask.incident_id == incident.id))
            session.delete(incident)
        session.commit()
    finally:
        session.close()


def _prepare_detections(client) -> list[str]:
    _cleanup_promoted_incidents()
    for scenario in ("combined_leak_pattern", "flow_surge", "pressure_drop"):
        _cleanup_detections()
        end = _unique_end()
        _ingest_scenario("SNS-HBR-007", scenario, 12, end)
        session = _session()
        try:
            DetectionEngine(session).run(sensor_external_id="SNS-HBR-007", now=end + timedelta(seconds=30))
        finally:
            session.close()
        items = client.get("/api/detections").json()["items"]
        if len(items) >= 2:
            return [item["detection_number"] for item in items]
    raise AssertionError("Could not prepare two screening detections for investigation tests")


def _review(client, detection_id: str, note: str = "Review started."):
    return client.post(
        f"/api/detections/{detection_id}/review",
        json={"actor_name": "Demo Operator", "note": note},
    )


def test_start_review_and_note_without_status_change(client, test_database) -> None:
    numbers = _prepare_detections(client)
    source = numbers[0]
    first = _review(client, source)
    assert first.status_code == 200
    assert first.json()["status"] == "under_review"
    assert first.json()["reviewed_by"] == "Demo Operator"
    assert "start_review" not in first.json()["allowed_actions"]
    assert "promote" in first.json()["allowed_actions"]

    again = _review(client, source)
    assert again.status_code == 200
    assert again.json()["status"] == "under_review"
    history = client.get(f"/api/detections/{source}/history").json()["events"]
    assert sum(1 for event in history if event["event_type"] == "review_started") == 1

    noted = client.post(
        f"/api/detections/{source}/notes",
        json={"actor_name": "Demo Operator", "note": "Neighbouring sensor also dropped."},
    )
    assert noted.status_code == 200
    assert noted.json()["status"] == "under_review"
    history = client.get(f"/api/detections/{source}/history").json()["events"]
    assert history[0]["created_at"] <= history[-1]["created_at"]
    assert history[-1]["event_type"] == "note_added"
    assert history[-1]["from_status"] == "under_review"
    assert history[-1]["to_status"] == "under_review"


def test_invalid_transitions_and_required_reason(client, test_database) -> None:
    numbers = _prepare_detections(client)
    source = numbers[0]
    promote = client.post(
        f"/api/detections/{source}/promote",
        json={
            "actor_name": "Demo Supervisor",
            "title": "Should fail",
            "severity": "tier_2",
            "classification": "suspected_leak",
            "summary": "Cannot promote from new.",
        },
    )
    assert promote.status_code == 409
    assert promote.json()["detail"]["code"] == "invalid_detection_transition"

    dismiss = client.post(f"/api/detections/{source}/dismiss", json={"actor_name": "Demo Operator"})
    assert dismiss.status_code == 422

    dismissed = client.post(
        f"/api/detections/{source}/dismiss",
        json={"actor_name": "Demo Operator", "reason_code": "sensor_fault", "note": "Unreliable battery."},
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"
    assert dismissed.json()["dismissal_reason"] == "sensor_fault"

    reopen = client.post(
        f"/api/detections/{source}/reopen",
        json={"actor_name": "Demo Supervisor", "note": "New corroborating telemetry."},
    )
    assert reopen.status_code == 200
    assert reopen.json()["status"] == "queued"
    assert reopen.json()["dismissal_reason"] is None

    missing = client.post("/api/detections/DET-999999/review", json=ACTOR)
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "detection_not_found"

    blank_actor = client.post(f"/api/detections/{source}/notes", json={"actor_name": "   ", "note": "x"})
    assert blank_actor.status_code == 422


def test_merge_rules(client, test_database) -> None:
    numbers = _prepare_detections(client)
    source, target = numbers[0], numbers[1]
    same = client.post(
        f"/api/detections/{source}/merge",
        json={"actor_name": "Demo Operator", "target_detection_id": source, "note": "self"},
    )
    assert same.status_code == 409
    assert same.json()["detail"]["code"] == "detection_merge_self"

    missing_target = client.post(
        f"/api/detections/{source}/merge",
        json={"actor_name": "Demo Operator", "target_detection_id": "DET-999999"},
    )
    assert missing_target.status_code == 404

    client.post(
        f"/api/detections/{target}/dismiss",
        json={"actor_name": "Demo Operator", "reason_code": "duplicate"},
    )
    into_terminal = client.post(
        f"/api/detections/{source}/merge",
        json={"actor_name": "Demo Operator", "target_detection_id": target},
    )
    assert into_terminal.status_code == 409
    assert into_terminal.json()["detail"]["code"] == "invalid_merge_target"

    client.post(
        f"/api/detections/{target}/reopen",
        json={"actor_name": "Demo Operator", "note": "Restore target."},
    )
    merged = client.post(
        f"/api/detections/{source}/merge",
        json={
            "actor_name": "Demo Operator",
            "target_detection_id": target,
            "note": "Same telemetry condition.",
        },
    )
    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "merged"
    assert body["merged_into_detection_id"] == target
    evidence_before = client.get(f"/api/detections/{source}/evidence").json()["items"]
    target_body = client.get(f"/api/detections/{target}").json()
    assert target_body["status"] in {"new", "queued", "under_review"}
    evidence_after = client.get(f"/api/detections/{source}/evidence").json()["items"]
    assert evidence_before == evidence_after

    mutate = client.post(f"/api/detections/{source}/notes", json={"actor_name": "Demo Operator", "note": "nope"})
    assert mutate.status_code == 409
    assert mutate.json()["detail"]["code"] == "detection_already_merged"

    history = client.get(f"/api/detections/{source}/history").json()["events"]
    assert history[-1]["event_type"] == "merged"
    assert history[-1]["target_detection_id"] == target


def test_promotion_transaction_and_idempotency(client, test_database) -> None:
    numbers = _prepare_detections(client)
    source = numbers[0]
    incident_total = client.get("/api/incidents").json()["total"]
    _review(client, source)

    session = _session()
    try:
        row = session.scalar(select(AnomalyDetection).where(AnomalyDetection.detection_number == source))
        evidence_snapshot = [
            (item.metric, item.observed_value, item.evidence_type)
            for item in session.scalars(select(DetectionEvidence).where(DetectionEvidence.detection_id == row.id))
        ]
    finally:
        session.close()

    promoted = client.post(
        f"/api/detections/{source}/promote",
        json={
            "actor_name": "Demo Supervisor",
            "title": "Suspected leak near Harbour District",
            "severity": "tier_2",
            "classification": "suspected_leak",
            "summary": "Promoted after manual review of corroborating pressure and flow evidence.",
            "note": "Operator confirmed that further field investigation is required.",
        },
    )
    assert promoted.status_code == 200, promoted.text
    payload = promoted.json()
    assert payload["detection"]["status"] == "promoted"
    incident_id = payload["incident"]["incident_number"]
    assert incident_id.startswith("INC-")
    assert payload["detection"]["incident_id"] == incident_id
    assert payload["incident"]["classification"] == "suspected_leak"
    assert client.get("/api/incidents").json()["total"] == incident_total + 1

    detail = client.get(f"/api/incidents/{incident_id}").json()
    assert detail["sensor"] == "SNS-HBR-007"
    timeline = client.get(f"/api/incidents/{incident_id}/timeline").json()["events"]
    assert any(event["event_type"] == "promoted_from_detection" for event in timeline)

    session = _session()
    try:
        row = session.scalar(select(AnomalyDetection).where(AnomalyDetection.detection_number == source))
        after = [
            (item.metric, item.observed_value, item.evidence_type)
            for item in session.scalars(select(DetectionEvidence).where(DetectionEvidence.detection_id == row.id))
        ]
        assert after == evidence_snapshot
        created = session.scalar(select(Incident).where(Incident.incident_number == incident_id))
        assert created is not None
        assert list(created.telemetry_points) == []
    finally:
        session.close()

    repeat = client.post(
        f"/api/detections/{source}/promote",
        json={
            "actor_name": "Demo Supervisor",
            "title": "Should not duplicate",
            "severity": "tier_2",
            "classification": "suspected_leak",
            "summary": "Second promote.",
        },
    )
    assert repeat.status_code == 409
    assert repeat.json()["detail"]["code"] == "detection_already_promoted"
    assert repeat.json()["detail"]["incident_id"] == incident_id
    assert client.get("/api/incidents").json()["total"] == incident_total + 1

    history = client.get(f"/api/detections/{source}/history").json()["events"]
    assert history[-1]["event_type"] == "promoted"
    assert history[-1]["incident_id"] == incident_id

    _cleanup_promoted_incidents()
    _cleanup_detections()
    assert client.get("/api/incidents").json()["total"] == incident_total


def test_concurrent_transition_protection(client, test_database) -> None:
    numbers = _prepare_detections(client)
    source = numbers[0]
    _review(client, source)
    results: list[int] = []

    def dismiss() -> None:
        response = client.post(
            f"/api/detections/{source}/dismiss",
            json={"actor_name": "Demo Operator", "reason_code": "other", "note": "race"},
        )
        results.append(response.status_code)

    def promote() -> None:
        response = client.post(
            f"/api/detections/{source}/promote",
            json={
                "actor_name": "Demo Supervisor",
                "title": "Race promote",
                "severity": "tier_2",
                "classification": "pressure_anomaly",
                "summary": "Concurrent promote.",
            },
        )
        results.append(response.status_code)

    first = Thread(target=dismiss)
    second = Thread(target=promote)
    first.start()
    second.start()
    first.join()
    second.join()
    assert 200 in results
    assert results.count(200) == 1
    assert 409 in results
    _cleanup_promoted_incidents()
    _cleanup_detections()


def test_existing_apis_still_compatible(client, test_database) -> None:
    _cleanup_promoted_incidents()
    incidents = client.get("/api/incidents")
    assert incidents.status_code == 200
    assert incidents.json()["total"] == 9
    assert client.get("/api/assets").status_code == 200
    assert client.get("/api/map/zones").status_code == 200
    assert client.get("/api/telemetry/sensors/SNS-HBR-007/latest").status_code == 200
    listing = client.get("/api/detections")
    assert listing.status_code == 200
    assert "items" in listing.json()

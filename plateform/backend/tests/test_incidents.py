import inspect

from sqlalchemy.exc import OperationalError

from app.api.routes import incidents as incidents_routes
from app.core.exceptions import DatabaseUnavailableError
from app.data.incidents import get_incidents
from app.repositories.incidents import IncidentRepository


def test_routes_do_not_read_in_memory_catalog() -> None:
    source = inspect.getsource(incidents_routes)
    assert "app.data.incidents" not in source
    assert "app.data" not in source


def test_incident_list(client) -> None:
    response = client.get("/api/incidents")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 9
    assert [item["id"] for item in payload["items"]] == [
        "INC-1835",
        "INC-1842",
        "INC-1838",
        "INC-1833",
        "INC-1841",
        "INC-1834",
        "INC-1836",
        "INC-1840",
        "INC-1837",
    ]
    assert {item["status"] for item in payload["items"]} <= {
        "investigating",
        "awaiting_approval",
        "resolved",
    }


def test_incident_detail_preserves_public_id(client) -> None:
    catalog = {incident.incident_number: incident for incident in get_incidents()}
    response = client.get("/api/incidents/INC-1835")
    assert response.status_code == 200
    payload = response.json()
    expected = catalog["INC-1835"]
    assert payload["id"] == "INC-1835"
    assert payload["incident_number"] == "INC-1835"
    assert payload["title"] == expected.title
    assert payload["confidence"] == expected.confidence
    assert payload["packet_loss_percent"] == expected.packet_loss_percent
    assert payload["pressure_change_bar"] == expected.pressure_change_bar
    assert payload["flow_change_m3h"] == expected.flow_change_m3h
    assert payload["sensor"] == expected.sensor
    assert payload["associated_valve"] == expected.associated_valve
    assert payload["zone"] == expected.zone
    assert len(payload["telemetry"]) == 16
    assert payload["telemetry"][10]["is_detection"] is True


def test_incident_timeline(client) -> None:
    response = client.get("/api/incidents/INC-1842/timeline")
    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "INC-1842"
    assert len(payload["events"]) >= 7
    ids = [event["id"] for event in payload["events"]]
    assert "INC-1842-evt-1" in ids
    first_catalog = next(event for event in payload["events"] if event["id"] == "INC-1842-evt-1")
    assert first_catalog["source"] == "detector"


def test_invalid_incident_number(client) -> None:
    response = client.get("/api/incidents/INC-0000")
    assert response.status_code == 404
    assert response.json()["detail"] == {
        "message": "Incident INC-0000 was not found.",
        "code": "incident_not_found",
    }


def test_severity_filter(client) -> None:
    response = client.get("/api/incidents", params={"severity": "tier_3"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert {item["incident_number"] for item in payload["items"]} == {"INC-1835", "INC-1842"}


def test_combined_search_and_status_filter(client) -> None:
    response = client.get(
        "/api/incidents",
        params={"search": "harbour", "status": "awaiting_approval"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["incident_number"] == "INC-1835"


def test_sort_detected_at_asc(client) -> None:
    response = client.get("/api/incidents", params={"sort_by": "detected_at", "sort_order": "asc"})
    assert response.status_code == 200
    numbers = [item["incident_number"] for item in response.json()["items"]]
    assert numbers[0] == "INC-1834"
    assert numbers[-1] == "INC-1836"


def test_incident_telemetry_ordering(client) -> None:
    response = client.get("/api/incidents/INC-1842")
    timestamps = [point["timestamp"] for point in response.json()["telemetry"]]
    assert timestamps == sorted(timestamps)
    assert response.json()["telemetry"][10]["is_detection"] is True


def test_incident_timeline_ordering(client) -> None:
    response = client.get("/api/incidents/INC-1842/timeline")
    timestamps = [event["timestamp"] for event in response.json()["events"]]
    assert timestamps == sorted(timestamps)


def test_dashboard_summary_uses_persisted_incidents(client) -> None:
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["active_incidents"] == 7
    assert payload["critical_incidents"] == 2
    assert payload["estimated_water_loss_m3"] == 75.4
    assert payload["total_sensors"] == 16
    assert payload["online_sensors"] == 12


def test_incident_list_database_outage_is_controlled(client, monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("driver"))

    monkeypatch.setattr(IncidentRepository, "list_incidents", fail)
    response = client.get("/api/incidents")
    assert response.status_code == 503
    payload = response.json()
    assert payload["detail"]["code"] == DatabaseUnavailableError.http_detail["code"]
    assert "driver" not in str(payload)
    assert "password" not in str(payload).lower()

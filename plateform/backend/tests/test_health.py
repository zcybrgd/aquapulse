def test_application_health_reports_database(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert payload["postgis"] == "available"
    assert payload["timescaledb"] == "available"
    assert "password" not in str(payload).lower()


def test_database_health_connected(client) -> None:
    response = client.get("/api/health/database")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert payload["postgis"] == "available"
    assert payload["timescaledb"] == "available"


def test_database_health_unavailable(client, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.health.database_is_reachable", lambda: False)
    response = client.get("/api/health/database")
    assert response.status_code == 503
    payload = response.json()
    assert payload["database"] == "unavailable"
    assert payload["postgis"] == "unavailable"
    assert payload["timescaledb"] == "unavailable"
    assert payload["detail"]["code"] == "database_unavailable"
    assert "127.0.0.1" not in str(payload)
    assert "password" not in str(payload).lower()


def test_health_stays_ok_when_database_is_down(client, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.health.database_is_reachable", lambda: False)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "unavailable"
    assert payload["postgis"] == "unavailable"
    assert payload["timescaledb"] == "unavailable"

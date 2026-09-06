from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Incident
from app.db.session import get_session_factory
from app.scripts.seed_database import seed_database


def test_seed_is_idempotent(test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.incidents == 9
    assert second.incidents == 9
    assert first.telemetry_points == second.telemetry_points == 144
    assert first.sensor_readings == second.sensor_readings
    assert first.sensor_readings > 0
    assert first.timeline_events == second.timeline_events == 69
    assert first.zones == second.zones == 9
    assert first.assets == second.assets
    assert first.assets == 35


def test_unique_incident_number_constraint(test_database) -> None:
    session = get_session_factory()()
    try:
        existing = session.scalar(select(Incident).limit(1))
        assert existing is not None
        session.add(
            Incident(
                id=uuid4(),
                incident_number=existing.incident_number,
                organization_id=existing.organization_id,
                zone_id=existing.zone_id,
                title=existing.title,
                classification=existing.classification,
                severity_tier=existing.severity_tier,
                status=existing.status,
                latitude=existing.latitude,
                longitude=existing.longitude,
                detected_at=existing.detected_at,
                updated_at=existing.updated_at,
                estimated_water_loss_m3=existing.estimated_water_loss_m3,
                estimated_loss_lps=existing.estimated_loss_lps,
                population_affected=existing.population_affected,
                current_summary=existing.current_summary,
                pressure_change_pct=existing.pressure_change_pct,
                flow_change_pct=existing.flow_change_pct,
                network_condition=existing.network_condition,
                signal_strength_dbm=existing.signal_strength_dbm,
                agent_investigation_summary=existing.agent_investigation_summary,
                recommended_action=existing.recommended_action,
                evidence=[],
                network_details={},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()

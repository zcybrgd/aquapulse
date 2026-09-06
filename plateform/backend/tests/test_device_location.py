import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.assets.connectivity import (
    assert_zone_segment_consistent,
    mask_device_msisdn,
    normalize_device_msisdn,
    normalize_location_label,
    public_zone_id,
)
from app.core.exceptions import AssetValidationError
from app.data.assets import DEVICE_LOCATION, get_asset_catalog
from app.db.models import Asset, PipelineSegment, Zone
from app.db.session import get_session_factory
from app.integrations.constants import CONTRACT_VERSION
from app.integrations.contracts.investigation import InvestigationRequestV1
from app.integrations.contracts.response import ResponseRequestV1
from app.scripts.seed_database import seed_database


def test_every_seeded_asset_has_direct_zone_and_label(test_database) -> None:
    session = get_session_factory()()
    try:
        assets = list(session.scalars(select(Asset)).all())
        assert len(assets) == 35
        for asset in assets:
            assert asset.zone_id is not None
            assert asset.location_label
            assert len(asset.location_label) <= 160
            if asset.pipeline_segment_id is not None:
                segment = session.get(PipelineSegment, asset.pipeline_segment_id)
                assert segment is not None
                assert segment.zone_id == asset.zone_id
    finally:
        session.close()


def test_catalog_assigns_demo_msisdn_only_to_cellular_devices() -> None:
    catalog = get_asset_catalog()
    assert len(catalog) == 35
    assert set(DEVICE_LOCATION) == {item["external_id"] for item in catalog}
    gateways = [item for item in catalog if item["asset_type"] == "gateway"]
    assert all(item["device_msisdn"] for item in gateways)
    valves = [item for item in catalog if item["asset_type"] == "valve"]
    assert all(item["device_msisdn"] is None for item in valves)
    sensors_with_sim = [item for item in catalog if item["asset_type"] == "sensor" and item["device_msisdn"]]
    assert 1 <= len(sensors_with_sim) < 16


def test_e164_normalization_and_masking() -> None:
    assert normalize_device_msisdn("  +971 50 000 4821 ") == "+971500004821"
    assert normalize_device_msisdn("") is None
    assert normalize_device_msisdn("   ") is None
    assert normalize_device_msisdn(None) is None
    assert mask_device_msisdn("+971500004821") == "+971•••••4821"
    assert mask_device_msisdn(None) is None
    with pytest.raises(AssetValidationError) as exc:
        normalize_device_msisdn("0501234567")
    assert exc.value.code == "invalid_device_msisdn"
    with pytest.raises(AssetValidationError):
        normalize_device_msisdn("+0971500004821")
    with pytest.raises(AssetValidationError):
        normalize_device_msisdn("+97150000482199999")
    with pytest.raises(AssetValidationError) as label_exc:
        normalize_location_label("x" * 161)
    assert label_exc.value.code == "invalid_location_label"
    assert normalize_location_label("  Harbour   District  ") == "Harbour District"


def test_migration_backfills_zone_from_pipeline_segment(test_database) -> None:
    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).where(Asset.pipeline_segment_id.is_not(None)))
        assert asset is not None
        expected_zone = session.scalar(
            select(PipelineSegment.zone_id).where(PipelineSegment.id == asset.pipeline_segment_id)
        )
        assert expected_zone is not None
        session.execute(text("ALTER TABLE assets ALTER COLUMN zone_id DROP NOT NULL"))
        session.execute(text("UPDATE assets SET zone_id = NULL WHERE id = :id"), {"id": asset.id})
        session.commit()
        session.execute(
            text(
                """
                UPDATE assets AS asset
                SET zone_id = segment.zone_id
                FROM pipeline_segments AS segment
                WHERE asset.pipeline_segment_id = segment.id
                  AND asset.zone_id IS NULL
                """
            )
        )
        session.commit()
        session.expire_all()
        restored = session.get(Asset, asset.id)
        assert restored is not None
        assert restored.zone_id == expected_zone
        missing = session.scalars(select(Asset.external_id).where(Asset.zone_id.is_(None))).all()
        assert missing == []
    finally:
        session.rollback()
        session.execute(
            text(
                """
                UPDATE assets AS asset
                SET zone_id = segment.zone_id
                FROM pipeline_segments AS segment
                WHERE asset.pipeline_segment_id = segment.id
                  AND asset.zone_id IS NULL
                """
            )
        )
        session.execute(text("ALTER TABLE assets ALTER COLUMN zone_id SET NOT NULL"))
        session.commit()
        session.close()


def test_zone_segment_mismatch_is_rejected(test_database) -> None:
    session = get_session_factory()()
    try:
        asset = session.scalar(
            select(Asset)
            .where(Asset.pipeline_segment_id.is_not(None))
            .options(joinedload(Asset.zone), joinedload(Asset.pipeline_segment))
        )
        other = session.scalar(select(Zone).where(Zone.id != asset.zone_id))
        assert asset is not None and other is not None
        asset.zone = other
        asset.zone_id = other.id
        with pytest.raises(AssetValidationError) as exc:
            assert_zone_segment_consistent(asset)
        assert exc.value.code == "asset_zone_segment_mismatch"
    finally:
        session.rollback()
        session.close()


def test_public_zone_id_format() -> None:
    assert public_zone_id("hbr") == "ZONE-HBR"


def test_duplicate_msisdn_rejected(test_database) -> None:
    session = get_session_factory()()
    try:
        first = session.scalar(select(Asset).where(Asset.device_msisdn.is_not(None)))
        second = session.scalar(select(Asset).where(Asset.device_msisdn.is_(None)))
        assert first is not None and second is not None
        second.device_msisdn = first.device_msisdn
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_invalid_msisdn_constraint(test_database) -> None:
    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).limit(1))
        assert asset is not None
        asset.device_msisdn = "not-a-number"
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_asset_and_map_responses_mask_msisdn(client) -> None:
    asset = client.get("/api/assets/HBR-GW-02").json()
    assert asset["zone"] == "Dubai Harbour"
    assert asset["zone_id"] == "ZONE-HBR"
    assert asset["zone_name"] == "Dubai Harbour"
    assert asset["location_label"] == "Harbour District – Pump Station 2"
    assert asset["has_cellular_identity"] is True
    assert asset["device_msisdn_masked"] == "+971•••••4821"
    assert "500004821" not in str(asset)
    assert asset["device_location"]["zone_id"] == "ZONE-HBR"
    assert asset["device_location"]["latitude"] == pytest.approx(25.09, abs=0.01)

    listed = client.get("/api/assets", params={"zone": "Dubai Harbour"}).json()
    ids = {item["external_id"] for item in listed["items"]}
    assert "SNS-HBR-007" in ids
    assert "HBR-GW-02" in ids
    assert "SNS-CRN-014" not in ids
    assert all("device_msisdn" not in item or item.get("device_msisdn") is None for item in listed["items"])

    sensor = client.get("/api/assets/SNS-CRN-014").json()
    assert sensor["has_cellular_identity"] is False
    assert sensor["device_msisdn_masked"] is None
    assert sensor["location_label"]

    mapped = client.get("/api/map/assets", params={"zone": "Dubai Harbour"}).json()
    harbour = next(item for item in mapped["features"] if item["id"] == "HBR-GW-02")
    assert harbour["properties"]["zone"] == "Dubai Harbour"
    assert harbour["properties"]["zone_id"] == "ZONE-HBR"
    assert harbour["properties"]["has_cellular_identity"] is True
    assert harbour["properties"]["device_msisdn_masked"] == "+971•••••4821"
    assert "500004821" not in str(mapped)


def test_search_includes_location_label(client) -> None:
    response = client.get("/api/assets", params={"search": "Valve Chamber 14"})
    assert response.status_code == 200
    assert response.json()["items"][0]["external_id"] == "VLV-CRN-014"


def test_agent_contract_version_unchanged() -> None:
    assert CONTRACT_VERSION == "1.0"
    assert "device_msisdn" not in InvestigationRequestV1.model_fields
    assert "location_label" not in InvestigationRequestV1.model_fields
    assert "device_msisdn" not in ResponseRequestV1.model_fields
    assert "operator_contact" in ResponseRequestV1.model_fields


def test_seed_location_is_idempotent(test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.assets == second.assets == 35
    session = get_session_factory()()
    try:
        gateway = session.scalar(select(Asset).where(Asset.external_id == "HBR-GW-02"))
        assert gateway is not None
        assert gateway.device_msisdn == "+971500004821"
        assert gateway.location_label == "Harbour District – Pump Station 2"
    finally:
        session.close()


def test_seed_does_not_overwrite_non_demo_msisdn(test_database) -> None:
    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
        assert asset is not None
        asset.device_msisdn = "+971555000014"
        meta = dict(asset.extra_metadata or {})
        meta.pop("demo_msisdn", None)
        asset.extra_metadata = meta
        session.commit()
    finally:
        session.close()

    seed_database()
    session = get_session_factory()()
    try:
        asset = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
        assert asset is not None
        assert asset.device_msisdn == "+971555000014"
        asset.device_msisdn = None
        session.commit()
    finally:
        session.close()

"""Extend assets with registry fields for sensors, valves and gateways."""

from alembic import op
import sqlalchemy as sa

revision = "0002_asset_registry"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("manufacturer", sa.String(length=120), nullable=True))
    op.add_column("assets", sa.Column("model", sa.String(length=120), nullable=True))
    op.add_column("assets", sa.Column("serial_number", sa.String(length=80), nullable=True))
    op.add_column("assets", sa.Column("firmware_version", sa.String(length=40), nullable=True))
    op.add_column("assets", sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("commissioned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("assets", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("assets", sa.Column("battery_pct", sa.Float(), nullable=True))
    op.add_column("assets", sa.Column("signal_strength_dbm", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("sampling_interval_seconds", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("last_maintenance_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("next_maintenance_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("control_mode", sa.String(length=20), nullable=True))
    op.add_column("assets", sa.Column("current_position", sa.String(length=20), nullable=True))
    op.add_column("assets", sa.Column("health_score", sa.Float(), nullable=True))

    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])
    op.create_index("ix_assets_operational_status", "assets", ["operational_status"])
    op.create_unique_constraint("uq_assets_serial_number", "assets", ["serial_number"])

    op.create_check_constraint(
        "ck_assets_battery_pct_range",
        "assets",
        "battery_pct IS NULL OR (battery_pct >= 0 AND battery_pct <= 100)",
    )
    op.create_check_constraint(
        "ck_assets_health_score_range",
        "assets",
        "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
    )
    op.create_check_constraint(
        "ck_assets_sampling_interval_positive",
        "assets",
        "sampling_interval_seconds IS NULL OR sampling_interval_seconds > 0",
    )
    op.create_check_constraint(
        "ck_assets_latitude_range",
        "assets",
        "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
    )
    op.create_check_constraint(
        "ck_assets_longitude_range",
        "assets",
        "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
    )
    op.create_check_constraint(
        "ck_assets_valve_position_allowed",
        "assets",
        "current_position IS NULL OR current_position IN ('open', 'closed', 'partial', 'unknown')",
    )
    op.create_check_constraint(
        "ck_assets_control_mode_allowed",
        "assets",
        "control_mode IS NULL OR control_mode IN ('manual', 'remote', 'automatic')",
    )
    op.create_check_constraint(
        "ck_assets_operational_status_allowed",
        "assets",
        "operational_status IN ('online', 'degraded', 'offline')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_assets_operational_status_allowed", "assets", type_="check")
    op.drop_constraint("ck_assets_control_mode_allowed", "assets", type_="check")
    op.drop_constraint("ck_assets_valve_position_allowed", "assets", type_="check")
    op.drop_constraint("ck_assets_longitude_range", "assets", type_="check")
    op.drop_constraint("ck_assets_latitude_range", "assets", type_="check")
    op.drop_constraint("ck_assets_sampling_interval_positive", "assets", type_="check")
    op.drop_constraint("ck_assets_health_score_range", "assets", type_="check")
    op.drop_constraint("ck_assets_battery_pct_range", "assets", type_="check")
    op.drop_constraint("uq_assets_serial_number", "assets", type_="unique")
    op.drop_index("ix_assets_operational_status", table_name="assets")
    op.drop_index("ix_assets_asset_type", table_name="assets")
    op.drop_column("assets", "health_score")
    op.drop_column("assets", "current_position")
    op.drop_column("assets", "control_mode")
    op.drop_column("assets", "next_maintenance_at")
    op.drop_column("assets", "last_maintenance_at")
    op.drop_column("assets", "sampling_interval_seconds")
    op.drop_column("assets", "signal_strength_dbm")
    op.drop_column("assets", "battery_pct")
    op.drop_column("assets", "longitude")
    op.drop_column("assets", "latitude")
    op.drop_column("assets", "commissioned_at")
    op.drop_column("assets", "installed_at")
    op.drop_column("assets", "firmware_version")
    op.drop_column("assets", "serial_number")
    op.drop_column("assets", "model")
    op.drop_column("assets", "manufacturer")

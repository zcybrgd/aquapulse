"""Device network snapshots for Nokia/CAMARA reachability and location.

Does not modify agent_audit_events or historical NETEVT records.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_device_network"
down_revision = "0012_incident_statuses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_network_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("source_mode", sa.String(length=32), nullable=False),
        sa.Column("reachability_status", sa.String(length=32), nullable=False),
        sa.Column("reachable_via", sa.String(length=32), nullable=True),
        sa.Column("reachability_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("network_location_available", sa.Boolean(), nullable=False),
        sa.Column("network_latitude", sa.Float(), nullable=True),
        sa.Column("network_longitude", sa.Float(), nullable=True),
        sa.Column("accuracy_radius_m", sa.Float(), nullable=True),
        sa.Column("location_area_type", sa.String(length=40), nullable=True),
        sa.Column("location_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_correlation_id", sa.String(length=80), nullable=True),
        sa.Column("raw_reachability_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_location_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.CheckConstraint(
            "reachability_status IN ('reachable', 'unreachable', 'unknown', 'not_supported', 'not_checked')",
            name="ck_device_network_snapshots_reachability_allowed",
        ),
        sa.CheckConstraint(
            "source_mode IN ('seeded_demo', 'nokia_simulator', 'nokia_live')",
            name="ck_device_network_snapshots_source_mode_allowed",
        ),
        sa.CheckConstraint(
            "network_latitude IS NULL OR (network_latitude >= -90 AND network_latitude <= 90)",
            name="ck_device_network_snapshots_latitude_range",
        ),
        sa.CheckConstraint(
            "network_longitude IS NULL OR (network_longitude >= -180 AND network_longitude <= 180)",
            name="ck_device_network_snapshots_longitude_range",
        ),
        sa.CheckConstraint(
            "accuracy_radius_m IS NULL OR accuracy_radius_m >= 0",
            name="ck_device_network_snapshots_accuracy_non_negative",
        ),
        sa.CheckConstraint(
            "(network_location_available = true AND network_latitude IS NOT NULL "
            "AND network_longitude IS NOT NULL) OR "
            "(network_location_available = false AND network_latitude IS NULL "
            "AND network_longitude IS NULL AND accuracy_radius_m IS NULL "
            "AND location_area_type IS NULL AND location_observed_at IS NULL)",
            name="ck_device_network_snapshots_location_consistency",
        ),
    )
    op.create_index("ix_device_network_snapshots_asset_id", "device_network_snapshots", ["asset_id"])
    op.create_index("ix_device_network_snapshots_retrieved_at", "device_network_snapshots", ["retrieved_at"])
    op.create_index(
        "ix_device_network_snapshots_reachability",
        "device_network_snapshots",
        ["reachability_status"],
    )
    op.create_index(
        "ix_device_network_snapshots_provider_source",
        "device_network_snapshots",
        ["provider", "source_mode"],
    )


def downgrade() -> None:
    op.drop_index("ix_device_network_snapshots_provider_source", table_name="device_network_snapshots")
    op.drop_index("ix_device_network_snapshots_reachability", table_name="device_network_snapshots")
    op.drop_index("ix_device_network_snapshots_retrieved_at", table_name="device_network_snapshots")
    op.drop_index("ix_device_network_snapshots_asset_id", table_name="device_network_snapshots")
    op.drop_table("device_network_snapshots")

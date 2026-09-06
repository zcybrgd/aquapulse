"""Initial AquaPulse incident persistence schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    op.create_table(
        "zones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_zones_organization_id_organizations", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_zones"),
        sa.UniqueConstraint("organization_id", "code", name="uq_zones_org_code"),
    )
    op.create_index("ix_zones_organization_id", "zones", ["organization_id"])

    op.create_table(
        "pipeline_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("upstream_node", sa.String(length=120), nullable=False),
        sa.Column("downstream_node", sa.String(length=120), nullable=False),
        sa.Column("criticality_score", sa.Integer(), nullable=False),
        sa.Column("population_served", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("criticality_score BETWEEN 1 AND 3", name="ck_pipeline_segments_criticality_range"),
        sa.CheckConstraint("population_served >= 0", name="ck_pipeline_segments_population_served_non_negative"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_pipeline_segments_organization_id_organizations", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name="fk_pipeline_segments_zone_id_zones", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_pipeline_segments"),
        sa.UniqueConstraint("organization_id", "external_id", name="uq_pipeline_segments_org_external_id"),
    )
    op.create_index("ix_pipeline_segments_organization_id", "pipeline_segments", ["organization_id"])
    op.create_index("ix_pipeline_segments_zone_id", "pipeline_segments", ["zone_id"])

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_segment_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("operational_status", sa.String(length=40), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("asset_type IN ('sensor', 'valve', 'gateway')", name="ck_assets_asset_type_allowed"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_assets_organization_id_organizations", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name="fk_assets_zone_id_zones", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pipeline_segment_id"], ["pipeline_segments.id"], name="fk_assets_pipeline_segment_id_pipeline_segments", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_assets"),
        sa.UniqueConstraint("organization_id", "external_id", name="uq_assets_org_external_id"),
    )
    op.create_index("ix_assets_organization_id", "assets", ["organization_id"])
    op.create_index("ix_assets_zone_id", "assets", ["zone_id"])
    op.create_index("ix_assets_pipeline_segment_id", "assets", ["pipeline_segment_id"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_number", sa.String(length=32), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_segment_id", sa.Uuid(), nullable=True),
        sa.Column("sensor_id", sa.Uuid(), nullable=True),
        sa.Column("valve_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("classification", sa.String(length=64), nullable=False),
        sa.Column("severity_tier", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_water_loss_m3", sa.Float(), nullable=False),
        sa.Column("estimated_loss_lps", sa.Float(), nullable=False),
        sa.Column("population_affected", sa.Integer(), nullable=False),
        sa.Column("current_summary", sa.String(length=2000), nullable=False),
        sa.Column("pressure_change_pct", sa.Float(), nullable=False),
        sa.Column("flow_change_pct", sa.Float(), nullable=False),
        sa.Column("network_condition", sa.String(length=300), nullable=False),
        sa.Column("signal_strength_dbm", sa.Integer(), nullable=False),
        sa.Column("packet_loss_pct", sa.Float(), nullable=True),
        sa.Column("assigned_operator", sa.String(length=120), nullable=True),
        sa.Column("agent_investigation_summary", sa.String(length=4000), nullable=False),
        sa.Column("recommended_action", sa.String(length=2000), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("network_details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("severity_tier BETWEEN 1 AND 3", name="ck_incidents_severity_tier_range"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_incidents_confidence_range"),
        sa.CheckConstraint("packet_loss_pct IS NULL OR (packet_loss_pct >= 0 AND packet_loss_pct <= 100)", name="ck_incidents_packet_loss_range"),
        sa.CheckConstraint("population_affected >= 0", name="ck_incidents_population_affected_non_negative"),
        sa.CheckConstraint("estimated_water_loss_m3 >= 0", name="ck_incidents_water_loss_non_negative"),
        sa.CheckConstraint("estimated_loss_lps >= 0", name="ck_incidents_loss_lps_non_negative"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_incidents_organization_id_organizations", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name="fk_incidents_zone_id_zones", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pipeline_segment_id"], ["pipeline_segments.id"], name="fk_incidents_pipeline_segment_id_pipeline_segments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sensor_id"], ["assets.id"], name="fk_incidents_sensor_id_assets", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["valve_id"], ["assets.id"], name="fk_incidents_valve_id_assets", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
        sa.UniqueConstraint("incident_number", name="uq_incidents_incident_number"),
    )
    op.create_index("ix_incidents_organization_id", "incidents", ["organization_id"])
    op.create_index("ix_incidents_zone_id", "incidents", ["zone_id"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_detected_at", "incidents", ["detected_at"])

    op.create_table(
        "incident_telemetry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pressure", sa.Float(), nullable=False),
        sa.Column("flow_rate", sa.Float(), nullable=False),
        sa.Column("packet_loss_pct", sa.Float(), nullable=False),
        sa.Column("is_detection_point", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("packet_loss_pct >= 0 AND packet_loss_pct <= 100", name="ck_incident_telemetry_telemetry_packet_loss_range"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name="fk_incident_telemetry_incident_id_incidents", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_incident_telemetry"),
    )
    op.create_index("ix_incident_telemetry_incident_id_timestamp", "incident_telemetry", ["incident_id", "timestamp"])

    op.create_table(
        "incident_timeline_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source IN ('detector', 'agent', 'network', 'operator', 'system')", name="ck_incident_timeline_events_timeline_source_allowed"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name="fk_incident_timeline_events_incident_id_incidents", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_incident_timeline_events"),
    )
    op.create_index("ix_incident_timeline_events_incident_id_timestamp", "incident_timeline_events", ["incident_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_incident_timeline_events_incident_id_timestamp", table_name="incident_timeline_events")
    op.drop_table("incident_timeline_events")
    op.drop_index("ix_incident_telemetry_incident_id_timestamp", table_name="incident_telemetry")
    op.drop_table("incident_telemetry")
    op.drop_index("ix_incidents_detected_at", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_zone_id", table_name="incidents")
    op.drop_index("ix_incidents_organization_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_assets_pipeline_segment_id", table_name="assets")
    op.drop_index("ix_assets_zone_id", table_name="assets")
    op.drop_index("ix_assets_organization_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_pipeline_segments_zone_id", table_name="pipeline_segments")
    op.drop_index("ix_pipeline_segments_organization_id", table_name="pipeline_segments")
    op.drop_table("pipeline_segments")
    op.drop_index("ix_zones_organization_id", table_name="zones")
    op.drop_table("zones")
    op.drop_table("organizations")

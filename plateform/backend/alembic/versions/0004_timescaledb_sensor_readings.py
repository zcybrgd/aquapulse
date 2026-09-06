"""Enable TimescaleDB and create the sensor_readings hypertable.

Unique indexes in TimescaleDB must include the partition key (`time`).
Deduplication of `source_message_id` is therefore enforced in the ingestion
service, with a lookup index on (sensor_id, source_message_id). A unique
constraint on (sensor_id, time, source_message_id) remains Timescale-legal.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_timescaledb_sensor_readings"
down_revision = "0003_postgis_map"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.create_table(
        "sensor_readings",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensor_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_message_id", sa.String(length=120), nullable=False),
        sa.Column("pressure_kpa", sa.Float(), nullable=True),
        sa.Column("flow_lps", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("signal_strength_dbm", sa.SmallInteger(), nullable=True),
        sa.Column("packet_loss_pct", sa.Float(), nullable=True),
        sa.Column("battery_pct", sa.Float(), nullable=True),
        sa.Column("quality_flags", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "("
            "pressure_kpa IS NOT NULL OR flow_lps IS NOT NULL OR temperature_c IS NOT NULL "
            "OR signal_strength_dbm IS NOT NULL OR packet_loss_pct IS NOT NULL "
            "OR battery_pct IS NOT NULL"
            ")",
            name="ck_sensor_readings_sensor_readings_has_measurement",
        ),
        sa.CheckConstraint(
            "packet_loss_pct IS NULL OR (packet_loss_pct >= 0 AND packet_loss_pct <= 100)",
            name="ck_sensor_readings_sensor_readings_packet_loss_range",
        ),
        sa.CheckConstraint(
            "battery_pct IS NULL OR (battery_pct >= 0 AND battery_pct <= 100)",
            name="ck_sensor_readings_sensor_readings_battery_range",
        ),
        sa.CheckConstraint(
            "received_at >= time - INTERVAL '1 hour'",
            name="ck_sensor_readings_sensor_readings_received_not_unreasonably_early",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sensor_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sensor_id", "time", name="pk_sensor_readings"),
        sa.UniqueConstraint(
            "sensor_id",
            "time",
            "source_message_id",
            name="uq_sensor_readings_sensor_time_source",
        ),
    )
    op.create_index(
        "ix_sensor_readings_sensor_time",
        "sensor_readings",
        ["sensor_id", sa.text("time DESC")],
        unique=False,
    )
    op.create_index(
        "ix_sensor_readings_org_time",
        "sensor_readings",
        ["organization_id", sa.text("time DESC")],
        unique=False,
    )
    op.create_index(
        "ix_sensor_readings_sensor_source",
        "sensor_readings",
        ["sensor_id", "source_message_id"],
        unique=False,
    )

    op.execute(
        "SELECT create_hypertable("
        "'sensor_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', "
        "if_not_exists => TRUE)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sensor_readings CASCADE")
    # Keep the TimescaleDB extension. Other objects may depend on it.
